import logging
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
from config import (
    GOOGLE_API_KEY,
    GRAPHITI_NEO4J_URI,
    GRAPHITI_NEO4J_USER,
    GRAPHITI_NEO4J_PASSWORD
)
from llm import llm

logger = logging.getLogger(__name__)

class Neo4jAIAgent:
    def __init__(self, group_id="fiware_data"):
        llm_cfg = LLMConfig(
            api_key=GOOGLE_API_KEY,
            model="gemini-2.0-flash",
            small_model="gemini-2.0-flash"
        )
        llm_client = GeminiClient(config=llm_cfg)
        embedder = GeminiEmbedder(config=GeminiEmbedderConfig(
            api_key=GOOGLE_API_KEY,
            embedding_model="embedding-001"
        ))
        reranker = GeminiRerankerClient(config=LLMConfig(
            api_key=GOOGLE_API_KEY,
            model="gemini-2.5-flash-lite-preview-06-17"
        ))
        self.graphiti = Graphiti(
            GRAPHITI_NEO4J_URI,
            GRAPHITI_NEO4J_USER,
            GRAPHITI_NEO4J_PASSWORD,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker
        )
        self.group_id = group_id
        logger.info("Neo4jAIAgent initialized.")

    async def answer_question(self, question: str, limit: int = 5) -> str:
        """
        Accepts a natural language question and returns an answer using Graphiti and the LLM.
        """
        config = COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        config.limit = limit
        # Search the knowledge graph for relevant nodes/edges
        search_result = await self.graphiti._search(
            query=question,
            group_ids=[self.group_id],
            config=config
        )
        # Gather facts from the top results
        facts = []
        for node in search_result.nodes:
            if hasattr(node, "fact") and node.fact:
                facts.append(node.fact)
            elif hasattr(node, "summary") and node.summary:
                facts.append(node.summary)
        for edge in search_result.edges:
            if hasattr(edge, "fact") and edge.fact:
                facts.append(edge.fact)
        # Compose a context for the LLM
        context = "\n".join(facts[:limit])
        if not context:
            return "I'm sorry, I could not find relevant information in the knowledge graph."
        # Use the LLM to generate an answer based on the context
        prompt = f"Answer the following question using the provided knowledge graph context.\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"
        response = await llm.ainvoke(prompt)
        return response.content 