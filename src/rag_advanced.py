"""
Advanced RAG features: Query rewriting and multi-hop reasoning
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any
import json


def create_query_rewriter_prompt():
    """Create prompt for query rewriting"""
    return ChatPromptTemplate.from_messages([
        ("system", """You are a query rewriting assistant. Your task is to improve medical queries for better information retrieval.

Given a user's question, rewrite it to:
1. Be more specific and clear
2. Include relevant medical terminology
3. Break down complex questions into key concepts
4. Maintain the original intent

Return ONLY the rewritten query, nothing else."""),
        ("human", "Original query: {original_query}\n\nRewritten query:")
    ])


def rewrite_query(llm, original_query: str) -> str:
    """Rewrite user query for better retrieval"""
    prompt = create_query_rewriter_prompt()
    chain = prompt | llm | StrOutputParser()
    rewritten = chain.invoke({"original_query": original_query})
    return rewritten.strip()


def create_multi_hop_prompt():
    """Create prompt for multi-hop reasoning"""
    return ChatPromptTemplate.from_messages([
        ("system", """You are a medical reasoning assistant. Analyze the retrieved context and determine if the question requires multiple steps to answer.

If the question can be answered directly from the context, return "DIRECT" followed by the answer.

If the question requires multiple steps or sub-questions, return "MULTI_HOP" followed by a JSON array of sub-questions that need to be answered first.

Format:
- DIRECT: [answer]
- MULTI_HOP: ["sub-question 1", "sub-question 2", ...]"""),
        ("human", "Question: {question}\n\nContext: {context}\n\nAnalysis:")
    ])


def analyze_query_complexity(llm, question: str, context: str) -> Dict[str, Any]:
    """Analyze if query requires multi-hop reasoning"""
    prompt = create_multi_hop_prompt()
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"question": question, "context": context})
    
    if result.startswith("DIRECT:"):
        return {
            "type": "direct",
            "answer": result.replace("DIRECT:", "").strip()
        }
    elif result.startswith("MULTI_HOP:"):
        try:
            sub_questions_json = result.replace("MULTI_HOP:", "").strip()
            sub_questions = json.loads(sub_questions_json)
            return {
                "type": "multi_hop",
                "sub_questions": sub_questions
            }
        except:
            return {
                "type": "direct",
                "answer": "Unable to parse multi-hop analysis. Proceeding with direct answer."
            }
    else:
        return {
            "type": "direct",
            "answer": result
        }


def multi_hop_reasoning(llm, retriever, original_query: str, max_hops: int = 2) -> Dict[str, Any]:
    """
    Perform multi-hop reasoning by breaking down complex queries
    
    Args:
        llm: Language model instance
        retriever: Document retriever
        original_query: Original user query
        max_hops: Maximum number of reasoning hops
    
    Returns:
        Dictionary with final answer and reasoning chain
    """
    def _retrieve(query):
        if hasattr(retriever, "invoke"):
            return retriever.invoke(query)
        return retriever(query)

    rewritten_query = rewrite_query(llm, original_query)
    
    initial_docs = _retrieve(rewritten_query)
    initial_context = "\n\n".join([doc.page_content for doc in initial_docs])
    
    analysis = analyze_query_complexity(llm, rewritten_query, initial_context)
    
    if analysis["type"] == "direct":
        return {
            "answer": analysis["answer"],
            "reasoning_chain": [rewritten_query],
            "context_used": initial_docs
        }
    
    reasoning_chain = [rewritten_query]
    all_contexts = list(initial_docs)
    
    for i, sub_question in enumerate(analysis["sub_questions"][:max_hops]):
        sub_docs = _retrieve(sub_question)
        all_contexts.extend(sub_docs)
        reasoning_chain.append(sub_question)
        
        if i >= max_hops - 1:
            break
    
    combined_context = "\n\n".join([doc.page_content for doc in all_contexts])
    
    synthesis_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a medical assistant. Synthesize information from multiple sources to answer the user's question comprehensively.

Use all the provided context to give a complete, accurate answer. Cite which parts of the context support your answer."""),
        ("human", "Original Question: {original_query}\n\nSub-questions explored:\n{sub_questions}\n\nCombined Context:\n{context}\n\nComprehensive Answer:")
    ])
    
    chain = synthesis_prompt | llm | StrOutputParser()
    final_answer = chain.invoke({
        "original_query": original_query,
        "sub_questions": "\n".join([f"- {q}" for q in reasoning_chain[1:]]),
        "context": combined_context
    })
    
    return {
        "answer": final_answer,
        "reasoning_chain": reasoning_chain,
        "context_used": all_contexts
    }

