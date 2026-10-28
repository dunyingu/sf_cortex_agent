AnswerRelevancy_prompt = """
You are a SQL expert. Please act as an impartial judge and evaluate the quality of the generated SQL response provided by the AI Assistant to the user question displayed below.
Your evaluation should consider RELEVANCY. You will be given a user question and the AI Assistant's answer.
Your job is to rate the assistant's response from 1 to 5, where 5 indicates you strongly agree that the response is
RELEVANT
and 1 indicates you strongly disagree.

Please note the column naming, column order or row order should NOT be considered for your evaluation.

Avoid any position biases and ensure that the order in which the content presented does not affect your evaluation.
Be as objective as possible. Output your rating with just the number rating value.

Only provide rating number without any explanations in your answer.

[User Question]
{question}

[The Start of the AI Assistant's Answer]
{gen_sql}
[The End of the AI Assistant's Answer]
"""


SemanticEquivalence_prompt = """
You are a SQL expert.Please act as an impartial judge and evaluate the quality of the generated SQL provided by the AI Assistant to the user question displayed below. 
You will be given a reference SQL answer and the AI Assistant's answer.
Your evaluation should consider the semantic similarity or equivalence between the AI generated SQL and reference SQL answer except for column naming, column ordering or row sorting. 
Your job is to rate the assistant's answer from 1 to 5, where 5 indicates you strongly agree that the response is
CORRECT
and 1 indicates you strongly disagree.

Please note the column naming, column order and row order should NOT be considered for your evaluation.

Avoid any position biases and ensure that the order in which the content presented does not affect your evaluation.
Be as objective as possible. Output your rating with just the number rating value.

Only provide rating number without any explanations in your answer.

[User Question]
{question}

[The Start of the Reference Answer]
{ref_sql}
[The End of the Reference Answer]

[The Start of the AI Assistant's Answer]
{gen_sql}
[The End of the AI Assistant's Answer]
"""


Correctness_prompt = """
You are a SQL expert.Please act as an impartial judge and evaluate the quality of the generated SQL provided by the AI Assistant to the user question displayed below.
Your evaluation should consider CORRECTNESS. 
You will be given a reference SQL answer and the AI Assistant's answer.
Your job is to rate the assistant's answer from 1 to 5, where 5 indicates you strongly agree that the response is
CORRECT
and 1 indicates you strongly disagree.

Please note the column naming, column order or row order should NOT be considered for your evaluation.

Avoid any position biases and ensure that the order in which the content presented does not affect your evaluation.
Be as objective as possible. Output your rating with just the number rating value.


Only provide rating number without any explanations in your answer.

[User Question]
{question}

[The Start of the Reference Answer]
{ref_sql}
[The End of the Reference Answer]

[The Start of the AI Assistant's Answer]
{gen_sql}
[The End of the AI Assistant's Answer]
"""


Comprehensiveness_prompt = """
You are a SQL expert. Please act as an impartial judge and evaluate the quality of the generated SQL response provided by the AI Assistant to the user question displayed below.
Your evaluation should consider THOROUGHNESS and COMPREHENSIVENESS. You will be given a reference SQL answer and the AI Assistant's answer.
Your job is to rate the assistant's response from 1 to 5, where 5 indicates you strongly agree that the response is
THOROUGH and COMPREHENSIVE
and 1 indicates you strongly disagree.

Please note the column naming, column order or row order should NOT be considered for your evaluation.

Avoid any position biases and ensure that the order in which the content presented does not affect your evaluation.
Be as objective as possible. Output your rating with just the number rating value.

Only provide rating number without any explanations in your answer.

[User Question]
{question}

[The Start of the Reference Answer]
{ref_sql}
[The End of the Reference Answer]

[The Start of the AI Assistant's Answer]
{gen_sql}
[The End of the AI Assistant's Answer]
"""


SQLAccuracy_bin_prompt = """You are evaluating JSON data against ground truth JSON data.
The JSON data is the output of a SQL query generated dataframe to answer a user question.
Please note the keys (columns in the dataframe) might not be displayed in the same order in the provided Inference JSON as those in the Groud Truth JSON. 
The records (rows in the dataframe) might not be sorted in the same order as well. 
The Inference JSON does not have to match the Ground Truth JSON perfectly but should contain the correct answer as denoted by the Ground Truth JSON.
You are to determine if the provided JSON data matches the ground truth JSON data regardless of key(column) naming or row/key(column) order and answers the user question.
Please note the key(column) naming, key(column) order or row order should NOT be considered for your evaluation.

Your answer should be either "True" or "False".
Answer "True" if you believe the Inference JSON data reflects the Ground Truth JSON data given the user question.
Otherwise, answer "False".
Only answer "True" or "False" without explanations.

[User Question]
{question}

[The Start of the Inference JSON Data]
{gen_js}
[The End of the Inference JSON Data]

[The Start of the Ground Truth Data]
{ref_js}
[The End of the Ground Truth Data]
"""


SQLAccuracy_prompt = """You are evaluating JSON data against ground truth JSON data.
The JSON data is the output of a SQL query generated dataframe to answer a user question.
Please note the keys (columns in the dataframe) might not be displayed in the same order in the provided Inference JSON as those in the Groud Truth JSON. 
The records (rows in the dataframe) might not be sorted in the same order as well. 
The Inference JSON does not have to match the Ground Truth JSON perfectly but should contain the correct answer as denoted by the Ground Truth JSON.
You are to determine if the provided JSON data matches the ground truth JSON data
and answers the user question.
Your job is to rate the equivalence of the Inferene JSON to the Ground Truth from 1 to 5 regardless of key(column) naming or row/key(column) order, where 5 indicates you strongly agree that the response is
Inference data is equivalent to the truth and 1 indicates you strongly disagree.
Please note the key(column) naming, key(column) order or row order should NOT be considered for your evaluation.

Only provide rating number without any explanations in your answer.

[User Question]
{question}

[The Start of the Inference JSON Data]
{gen_js}
[The End of the Inference JSON Data]

[The Start of the Ground Truth Data]
{ref_js}
[The End of the Ground Truth Data]
"""


Fix_prompt = """
You are a SQL expert.
Please act as an impartial judge and review the quality of the generated SQL provided by the AI Assistant to the user question displayed below. 
You will be given a reference SQL answer and the AI Assistant's answer.
Your review should consider the relevancy, correctness and comprehensiveness of the AI generated SQL as well as its semantic similarity or closeness to the reference SQL answer EXCEPT for column naming, column ordering or row sorting. 
Your job is to provide CONCISE improvement suggestion(s) for the AI generated SQL if any, by considering the above mentioned criteria (relevancy, correctness, comprehensiveness and semantic closeness to the reference anwser).

Please note column naming, column order or row order should NOT be included in your improvement suggestion(s).

Chances are that the AI generated SQL is perfect requiring no improvement, then you just answer 'NULL' in your response.
Output the CONCISE improvement suggestions only or 'NULL' if no improvement is required, without any explanations.

[User Question]
{question}

[The Start of the Reference Answer]
{ref_sql}
[The End of the Reference Answer]

[The Start of the AI Assistant's Answer]
{gen_sql}
[The End of the AI Assistant's Answer]
"""