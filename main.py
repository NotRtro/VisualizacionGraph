from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import json
from itertools import combinations
import os
import uvicorn
from pathlib import Path

app = FastAPI(title="UTEC Network Visualization", version="1.0.0")

def procesar_datos_profesores():
    """Procesa los datos de profesores y genera el grafo"""
    try:
        # Cargar datos desde CSV
        if not os.path.exists("profesores_utec.csv"):
            raise FileNotFoundError("No se encontró el archivo profesores_utec.csv")
        
        df = pd.read_csv("profesores_utec.csv")
        
        # Limpiar afiliaciones
        def limpiar_afiliacion(texto):
            if pd.isna(texto):
                return ""
            return texto.split(" - ")[0].strip()
        
        for col in ["afiliacion_1", "afiliacion_2", "afiliacion_3", "afiliacion_4"]:
            if col in df.columns:
                df[col] = df[col].apply(limpiar_afiliacion)
        
        df.fillna("", inplace=True)
        
        # Crear nodos
        nodes = []
        for i, row in df.iterrows():
            nodes.append({
                "id": row["nombre"],
                "name": row["nombre"],
                "correo": row.get("correo", ""),
                "group": row["afiliacion_1"] if pd.notna(row["afiliacion_1"]) and row["afiliacion_1"] != "" else "Sin grupo",
                "description": f"Afiliación: {row['afiliacion_1']}"
            })
        
        # Crear enlaces únicos
        unique_links = set()
        for aff_col in ["afiliacion_1", "afiliacion_2", "afiliacion_3", "afiliacion_4"]:
            if aff_col not in df.columns:
                continue
                
            grupos = df.groupby(aff_col)
            for group_name, group_df in grupos:
                if pd.isna(group_name) or group_name == "":
                    continue
                
                nombres = group_df["nombre"].tolist()
                
                # Filtrar grupos muy grandes o muy pequeños
                if len(nombres) > 10 or len(nombres) < 2:
                    continue
                
                # Crear enlaces entre todos los miembros del grupo
                for source, target in combinations(sorted(nombres), 2):
                    unique_links.add((source, target))
        
        links = [{"source": s, "target": t, "value": 1} for s, t in unique_links]
        
        graph = {"nodes": nodes, "links": links}
        
        return graph
    
    except Exception as e:
        print(f"Error procesando datos: {e}")
        return {"nodes": [], "links": []}

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Red de Profesores UTEC</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 300;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            
            .header p {
                margin: 10px 0 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }
            
            .visualization-container {
                padding: 30px;
                background: #f8f9fa;
            }
            
            .controls {
                margin-bottom: 20px;
                text-align: center;
            }
            
            .control-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                margin: 0 5px;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 500;
            }
            
            .control-btn:hover {
                background: #5a67d8;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            
            #network-container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                overflow: hidden;
            }
            
            .tooltip {
                position: absolute;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-size: 12px;
                pointer-events: none;
                opacity: 0;
                z-index: 1000;
                max-width: 250px;
                line-height: 1.4;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            }
            
            .stats {
                display: flex;
                justify-content: space-around;
                margin: 20px 0;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }
            
            .stat-item {
                text-align: center;
            }
            
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: #667eea;
                display: block;
            }
            
            .stat-label {
                color: #666;
                font-size: 0.9rem;
                margin-top: 5px;
            }
            
            .loading {
                text-align: center;
                padding: 50px;
                color: #666;
                font-size: 1.2rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Red de Colaboración UTEC</h1>
                <p>Visualización de la red de profesores e investigadores</p>
            </div>
            
            <div class="visualization-container">
                <div class="stats" id="stats">
                    <div class="stat-item">
                        <span class="stat-number" id="nodes-count">-</span>
                        <span class="stat-label">Profesores</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="links-count">-</span>
                        <span class="stat-label">Conexiones</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="groups-count">-</span>
                        <span class="stat-label">Departamentos</span>
                    </div>
                </div>
                
                <div class="controls">
                    <button class="control-btn" onclick="resetSimulation()">Reiniciar Posiciones</button>
                    <button class="control-btn" onclick="toggleLabels()">Mostrar/Ocultar Nombres</button>
                    <button class="control-btn" onclick="centerGraph()">Centrar Vista</button>
                </div>
                
                <div id="network-container">
                    <div class="loading">Cargando datos de la red...</div>
                </div>
            </div>
        </div>
        
        <script>
            let simulation, svg, nodes, links, nodeElements, linkElements, labelElements;
            let showLabels = true;
            const width = 1140;
            const height = 600;
            
            // Crear tooltip
            const tooltip = d3.select("body").append("div")
                .attr("class", "tooltip");
            
            async function loadData() {
                try {
                    const response = await fetch('/api/graph-data');
                    const graphData = await response.json();
                    
                    if (graphData.nodes.length === 0) {
                        document.getElementById('network-container').innerHTML = 
                            '<div class="loading">No se pudieron cargar los datos. Asegúrate de que el archivo profesores_utec.csv esté presente.</div>';
                        return;
                    }
                    
                    createVisualization(graphData);
                    updateStats(graphData);
                } catch (error) {
                    console.error('Error cargando datos:', error);
                    document.getElementById('network-container').innerHTML = 
                        '<div class="loading">Error cargando los datos de la red.</div>';
                }
            }
            
            function updateStats(graphData) {
                document.getElementById('nodes-count').textContent = graphData.nodes.length;
                document.getElementById('links-count').textContent = graphData.links.length;
                
                const uniqueGroups = new Set(graphData.nodes.map(n => n.group));
                document.getElementById('groups-count').textContent = uniqueGroups.size;
            }
            
            function createVisualization(graphData) {
                document.getElementById('network-container').innerHTML = '';
                
                const color = d3.scaleOrdinal(d3.schemeCategory10);
                
                nodes = graphData.nodes.map(d => ({...d}));
                links = graphData.links.map(d => ({...d}));
                
                // Inicializar posiciones
                nodes.forEach(d => {
                    d.x = width / 2 + Math.random() * 100 - 50;
                    d.y = height / 2 + Math.random() * 100 - 50;
                });
                
                svg = d3.select("#network-container")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .attr("viewBox", [0, 0, width, height]);
                
                // Configurar simulación
                simulation = d3.forceSimulation(nodes)
                    .force("link", d3.forceLink(links).id(d => d.id).distance(80))
                    .force("charge", d3.forceManyBody().strength(-150))
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collide", d3.forceCollide().radius(20));
                
                // Crear enlaces
                linkElements = svg.append("g")
                    .attr("stroke", "#999")
                    .attr("stroke-opacity", 0.4)
                    .selectAll("line")
                    .data(links)
                    .join("line")
                    .attr("stroke-width", 1.5);
                
                // Crear nodos
                nodeElements = svg.append("g")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 2)
                    .selectAll("circle")
                    .data(nodes)
                    .join("circle")
                    .attr("r", 8)
                    .attr("fill", d => color(d.group))
                    .style("cursor", "pointer")
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended));
                
                // Crear etiquetas
                labelElements = svg.append("g")
                    .selectAll("text")
                    .data(nodes)
                    .join("text")
                    .text(d => d.name.split(' ').slice(0, 2).join(' '))
                    .attr("font-size", "10px")
                    .attr("font-family", "Arial, sans-serif")
                    .attr("dx", 12)
                    .attr("dy", 3)
                    .style("pointer-events", "none")
                    .style("fill", "#333");
                
                // Event listeners
                nodeElements
                    .on("mouseover", showTooltip)
                    .on("mousemove", moveTooltip)
                    .on("mouseout", hideTooltip)
                    .on("click", highlightConnections);
                
                // Actualizar posiciones en cada tick
                simulation.on("tick", () => {
                    // Mantener nodos dentro del área visible
                    nodes.forEach(d => {
                        d.x = Math.max(15, Math.min(width - 15, d.x));
                        d.y = Math.max(15, Math.min(height - 15, d.y));
                    });
                    
                    linkElements
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);
                    
                    nodeElements
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);
                    
                    labelElements
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                });
            }
            
            function showTooltip(event, d) {
                const connections = links.filter(l => l.source === d || l.target === d).length;
                const content = `
                    <strong>${d.name}</strong><br/>
                    ${d.correo ? `📧 ${d.correo}<br/>` : ''}
                    ${d.group ? `🏛️ ${d.group}<br/>` : ''}
                    🔗 ${connections} conexiones
                `;
                
                tooltip.html(content)
                    .style("opacity", 1);
                
                highlightNode(d);
            }
            
            function moveTooltip(event) {
                tooltip
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px");
            }
            
            function hideTooltip() {
                tooltip.style("opacity", 0);
                clearHighlight();
            }
            
            function highlightNode(targetNode) {
                const connectedLinks = links.filter(l => 
                    l.source === targetNode || l.target === targetNode
                );
                const connectedNodes = new Set();
                connectedLinks.forEach(l => {
                    connectedNodes.add(l.source);
                    connectedNodes.add(l.target);
                });
                
                nodeElements.style("opacity", d => connectedNodes.has(d) ? 1 : 0.2);
                linkElements.style("opacity", l => 
                    l.source === targetNode || l.target === targetNode ? 0.8 : 0.1
                );
                labelElements.style("opacity", d => connectedNodes.has(d) ? 1 : 0.2);
            }
            
            function clearHighlight() {
                nodeElements.style("opacity", 1);
                linkElements.style("opacity", 0.4);
                labelElements.style("opacity", showLabels ? 1 : 0);
            }
            
            function highlightConnections(event, d) {
                highlightNode(d);
            }
            
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }
            
            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }
            
            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
            
            function resetSimulation() {
                if (simulation) {
                    simulation.alpha(1).restart();
                }
            }
            
            function toggleLabels() {
                showLabels = !showLabels;
                if (labelElements) {
                    labelElements.style("opacity", showLabels ? 1 : 0);
                }
            }
            
            function centerGraph() {
                if (simulation) {
                    simulation.force("center", d3.forceCenter(width / 2, height / 2));
                    simulation.alpha(0.3).restart();
                }
            }
            
            // Cargar datos al iniciar
            loadData();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/graph-data")
async def get_graph_data():
    """API endpoint que devuelve los datos del grafo"""
    try:
        graph_data = procesar_datos_profesores()
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando datos: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """API endpoint que devuelve estadísticas de la red"""
    try:
        graph_data = procesar_datos_profesores()
        
        # Calcular estadísticas
        num_nodes = len(graph_data["nodes"])
        num_links = len(graph_data["links"])
        
        # Grupos únicos
        unique_groups = set(node["group"] for node in graph_data["nodes"])
        num_groups = len(unique_groups)
        
        # Densidad de la red
        max_possible_links = num_nodes * (num_nodes - 1) / 2
        density = num_links / max_possible_links if max_possible_links > 0 else 0
        
        return {
            "nodes": num_nodes,
            "links": num_links,
            "groups": num_groups,
            "density": round(density, 4),
            "avg_connections": round(2 * num_links / num_nodes, 2) if num_nodes > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando estadísticas: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
