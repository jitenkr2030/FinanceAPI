from fastapi import HTTPException

def not_found(detail="Resource not found"):
    raise HTTPException(status_code=404, detail=detail)

def bad_request(detail="Bad request"):
    raise HTTPException(status_code=400, detail=detail)
