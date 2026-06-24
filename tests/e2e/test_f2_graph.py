# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

import uuid
import pytest
from fastapi.testclient import TestClient
from research_engine.models import KnowledgeGraph, KGNode, KGEdge
from research_engine.output.storage import save_knowledge_graph, load_knowledge_graph
from tests.e2e.conftest import mock_db, DEFAULT_WORKSPACE_ID

@pytest.fixture
def run_id_in_db() -> str:
    """Fixture that inserts a mock run to research_runs and returns its ID."""
    run_id = str(uuid.uuid4())
    mock_db["research_runs"].append({
        "id": run_id,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "query": "quantum gravity",
        "model_used": "mock-model",
        "status": "complete",
        "progress": 100,
        "created_at": "2026-06-18T00:00:00Z"
    })
    return run_id

@pytest.mark.asyncio
async def test_graph_write_nodes_edges(run_id_in_db: str):
    """Happy Path: Persists node and edge models to graph_nodes and graph_edges tables."""
    # 1. Create a dummy KnowledgeGraph
    kg = KnowledgeGraph(
        run_id=run_id_in_db,
        nodes=[
            KGNode(id="n1", label="Node 1", type="concept", community=0, degree=1, summary="Concept 1"),
            KGNode(id="n2", label="Node 2", type="technology", community=0, degree=1, summary="Concept 2")
        ],
        edges=[
            KGEdge(source="n1", target="n2", type="semantically_similar_to", confidence=0.9, label="link")
        ]
    )
    
    # 2. Save knowledge graph (which writes to mock Supabase DB)
    await save_knowledge_graph(kg, run_id_in_db)
    
    # 3. Assert mock database has stored the nodes and edges
    assert len(mock_db["graph_nodes"]) == 2
    assert len(mock_db["graph_edges"]) == 1
    assert mock_db["graph_nodes"][0]["run_id"] == run_id_in_db
    assert mock_db["graph_nodes"][0]["id"] == "n1"
    assert mock_db["graph_edges"][0]["source"] == "n1"
    assert mock_db["graph_edges"][0]["target"] == "n2"

def test_graph_read_nodes_edges(run_id_in_db: str):
    """Happy Path: Loads correct node/edge structure by run_id from DB."""
    # Pre-populate database
    mock_db["graph_nodes"].extend([
        {"run_id": run_id_in_db, "id": "n1", "label": "Node 1", "type": "concept", "community": 0, "degree": 1, "summary": "Concept 1", "confidence": 1.0, "file_path": "", "embedding": [0.1]*1536},
        {"run_id": run_id_in_db, "id": "n2", "label": "Node 2", "type": "concept", "community": 0, "degree": 1, "summary": "Concept 2", "confidence": 1.0, "file_path": "", "embedding": [0.2]*1536}
    ])
    mock_db["graph_edges"].append({
        "run_id": run_id_in_db,
        "source": "n1",
        "target": "n2",
        "type": "semantically_similar_to",
        "confidence": 0.9,
        "label": "link"
    })
    
    # Load from storage (patched to read from DB)
    loaded_kg = load_knowledge_graph(run_id_in_db)
    assert len(loaded_kg.nodes) == 2
    assert len(loaded_kg.edges) == 1
    assert loaded_kg.nodes[0].id == "n1"
    assert loaded_kg.edges[0].source == "n1"

def test_similarity_rpc_exact_match(e2e_test_client: TestClient, run_id_in_db: str):
    """Happy Path: RPC match_graph_nodes finds exact query embedding with similarity ~1.0."""
    # Insert node with precise embedding
    emb = [0.0] * 1536
    emb[0] = 1.0 # Unit vector
    
    mock_db["graph_nodes"].append({
        "run_id": run_id_in_db,
        "id": "exact_match_node",
        "label": "Exact Match",
        "type": "concept",
        "embedding": emb,
        "summary": "matching test node"
    })
    
    # Query with exact same embedding
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": emb, "match_threshold": 0.9, "match_count": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "exact_match_node"
    assert abs(data[0]["similarity"] - 1.0) < 1e-5

def test_similarity_rpc_under_threshold(e2e_test_client: TestClient, run_id_in_db: str):
    """Happy Path: Query returns no results if threshold is set to 1.0 (strict) and match is slightly below."""
    emb_node = [0.0] * 1536
    emb_node[0] = 1.0
    
    mock_db["graph_nodes"].append({
        "run_id": run_id_in_db,
        "id": "approx_match_node",
        "label": "Approx Match",
        "type": "concept",
        "embedding": emb_node
    })
    
    # Query with slightly different embedding (orthogonal vector)
    query_emb = [0.0] * 1536
    query_emb[1] = 1.0
    
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": query_emb, "match_threshold": 0.5, "match_count": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Similarity is 0.0, which is below 0.5 threshold

def test_similarity_rpc_default_limit(e2e_test_client: TestClient, run_id_in_db: str):
    """Happy Path: Respects max results limit when finding matching nodes."""
    emb = [0.0] * 1536
    emb[0] = 1.0
    
    for i in range(10):
        mock_db["graph_nodes"].append({
            "run_id": run_id_in_db,
            "id": f"node_{i}",
            "label": f"Node {i}",
            "type": "concept",
            "embedding": emb
        })
        
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": emb, "match_threshold": 0.0, "match_count": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

def test_similarity_invalid_threshold(e2e_test_client: TestClient, run_id_in_db: str):
    """Boundary/Corner: Similarity threshold < -1.0 or > 1.0 returns HTTP 400."""
    emb = [0.0] * 1536
    emb[0] = 1.0
    
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": emb, "match_threshold": 1.1}
    )
    assert response.status_code == 400
    
    response2 = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": emb, "match_threshold": -1.05}
    )
    assert response2.status_code == 400

@pytest.mark.asyncio
async def test_graph_write_isolated_nodes(run_id_in_db: str):
    """Boundary/Corner: Persists nodes with no edges without failing integrity."""
    kg = KnowledgeGraph(
        run_id=run_id_in_db,
        nodes=[
            KGNode(id="isolated_node", label="Isolated", type="concept")
        ],
        edges=[]
    )
    await save_knowledge_graph(kg, run_id_in_db)
    assert len(mock_db["graph_nodes"]) == 1
    assert len(mock_db["graph_edges"]) == 0

def test_graph_read_nonexistent_run():
    """Boundary/Corner: Reading knowledge graph for missing run returns HTTP 404."""
    # We test load_knowledge_graph directly since it raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_knowledge_graph("nonexistent-run-id-123")

def test_similarity_empty_query_embedding(e2e_test_client: TestClient, run_id_in_db: str):
    """Boundary/Corner: Passing empty or null embedding vector returns HTTP 400."""
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": [], "match_threshold": 0.5}
    )
    assert response.status_code in (400, 422)

def test_similarity_rpc_negative_threshold(e2e_test_client: TestClient, run_id_in_db: str):
    """Boundary/Corner: Cosine similarity search with negative threshold (-1.0) returns all nodes."""
    emb = [0.0] * 1536
    emb[0] = 1.0
    
    mock_db["graph_nodes"].extend([
        {"run_id": run_id_in_db, "id": "n1", "label": "Node 1", "embedding": emb},
        {"run_id": run_id_in_db, "id": "n2", "label": "Node 2", "embedding": [-x for x in emb]} # Opposite vector
    ])
    
    response = e2e_test_client.post(
        f"/runs/{run_id_in_db}/knowledge-graph/similarity",
        json={"query_embedding": emb, "match_threshold": -1.0, "match_count": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
