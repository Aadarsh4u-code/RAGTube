from langchain_core.prompts import PromptTemplate

my_prompt = PromptTemplate(
    template="""
        You are a helpful assistant.
        Answer ONLY from the provided transcript context.
        If the context is insufficient, just say you don't know.

        {context}
        Question: {question}
    """,
    input_variables=['context', 'question']
)

def apply_prompt(inputs):
    context = inputs['context']
    question = inputs['question']
    return my_prompt.invoke({"context": context, "question": question})

