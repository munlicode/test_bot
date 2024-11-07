import openai
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import time

PINECONE_API_KEY=""
pc = Pinecone(api_key=PINECONE_API_KEY)
spec = ServerlessSpec(cloud="aws", region="us-east-1")
index_name ="business-data"
if index_name not in pc.list_indexes().names():
    pc.create_index(
    name=index_name,
    dimension=1536,  # This should match the dimension of your embeddings
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    ),
    deletion_protection="disabled"
    )
    # wait for index to be initialized
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)

index = pc.Index(index_name)

total_tokens = 0

def get_embeddings(text, EMBEDD_MODEL='text-embedding-3-small'):
    response = openai.embeddings.create(
        input=text,
        model=EMBEDD_MODEL
    )
    total_tokens += response.usage.total_tokens
    return response.data[0].embedding

def upload_data_to_pinecone(texts):
    for key, text in texts.items():
        embedding = get_embeddings(text)
        index.upsert([
            {
                'id': key,
                'values': embedding,
                'metadata': {'text': text}
            }
        ])
def get_relevant_context(query, EMBEDD_MODEL='text-embedding-3-small', TOP_K=None, SCORE=None):
    try:
        # Embedd user message
        query_embedding = openai.embeddings.create(
            input=[query],
            model=EMBEDD_MODEL
        )
        query_embedding_vectors = query_embedding.data[0].embedding

        # Collect Used Tokens
        usage = query_embedding.usage
        total_tokens += usage.total_tokens

        # Setting most relevant answers to default
        if not TOP_K:
            TOP_K == 5

        # Extract most relevant metadata from vector database
        results = index.query(
            vector=query_embedding_vectors,
            top_k=TOP_K,
            include_metadata=True
        )

        # Extract and process relevant information 
        relevant_info  =[]
        for match in results.matches:
            if SCORE:
                if match.score < SCORE:
                    continue
            text = match.metadata
            if text:
                relevant_info.append(f"{text} (Similarity: {match.score:.2f})")
        if relevant_info:
            return "\n".join(relevant_info)
        else:
            return "No relevant information found."
    except Exception as e:
        print(f"Error in get_relevant_context: {e}")
        return "Error retrieving context."


def generate_response(USER_MESSAGE, SYSTEM_INSTRUCTIONS, CONVERSATION_HISTORY=None, TOP_K=None, SCORE=None, MESSAGE_MODEL='gpt-4-turbo', MAX_TOKENS=None, TEMPERATURE=None, TOP_P=1, FREQUENCY_PENALTY=0, PRESENCE_PENALTY=0):
    relevant_context = get_relevant_context(USER_MESSAGE, TOP_K, SCORE)
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "assistant", "content": f"Relevant business information: {' '.join(relevant_context)}"},
        *CONVERSATION_HISTORY,
        {"role": "user", "content": USER_MESSAGE}
    ]
    try:
        response = openai.chat.completions.create(
            model=MESSAGE_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY
        )

        total_tokens += response.usage.total_tokens
    except openai.error.OpenAIError as e:
        print(f"An error occurred: {e}")
        return "I'm sorry, I'm having trouble generating a response right now. Please try again later."
        
    return response.choices[0].message.content.strip()
