from fastapi.routing import APIRoute

from app.main import app


def test_matching_route_contracts_are_registered() -> None:
    methods_by_path = {
        route.path: route.methods for route in app.routes if isinstance(route, APIRoute)
    }
    assert "POST" in methods_by_path["/reconciliation-runs/{run_id}/run"]
    assert "GET" in methods_by_path["/reconciliation-runs/{run_id}/results"]
    assert "GET" in methods_by_path["/reconciliation-runs/{run_id}/export"]
    assert "POST" in methods_by_path["/match-results/{match_id}/approve"]
    assert "POST" in methods_by_path["/match-results/{match_id}/reject"]
    assert "POST" in methods_by_path["/files/{file_id}/normalize"]
    assert "GET" in methods_by_path["/files/{file_id}/rejected-records"]
