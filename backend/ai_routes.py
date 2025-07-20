from fastapi import APIRouter, Request, Body, HTTPException

router = APIRouter()

@router.post("/ai/ask")
async def ai_ask(request: Request, body: dict = Body(...)):
    """
    Accepts: {"question": "your question here"}
    Returns: {"answer": "..."}
    """
    agent = request.app.state.ai_agent
    question = body.get("question")
    if not question or not isinstance(question, str):
        raise HTTPException(status_code=400, detail="Missing or invalid question.")
    try:
        answer = await agent.answer_question(question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 