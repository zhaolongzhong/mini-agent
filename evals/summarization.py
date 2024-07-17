import os

import matplotlib.pyplot as plt
import numpy as np
import openai
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv(dotenv_path=".env")

# Reference: https://github.com/openai/openai-cookbook/blob/main/examples/evaluation/How_to_eval_abstractive_summarization.ipynb
excerpt = "OpenAI's mission is to ensure that artificial general intelligence (AGI) benefits all of humanity. OpenAI will build safe and beneficial AGI directly, but will also consider its mission fulfilled if its work aids others to achieve this outcome. OpenAI follows several key principles for this purpose. First, broadly distributed benefits - any influence over AGI's deployment will be used for the benefit of all, and to avoid harmful uses or undue concentration of power. Second, long-term safety - OpenAI is committed to doing the research to make AGI safe, and to promote the adoption of such research across the AI community. Third, technical leadership - OpenAI aims to be at the forefront of AI capabilities. Fourth, a cooperative orientation - OpenAI actively cooperates with other research and policy institutions, and seeks to create a global community working together to address AGI's global challenges."
ref_summary = "OpenAI aims to ensure artificial general intelligence (AGI) is used for everyone's benefit, avoiding harmful uses or undue power concentration. It is committed to researching AGI safety, promoting such studies among the AI community. OpenAI seeks to lead in AI capabilities and cooperates with global research and policy institutions to address AGI's challenges."
eval_summary_1 = "OpenAI aims to AGI benefits all humanity, avoiding harmful uses and power concentration. It pioneers research into safe and beneficial AGI and promotes adoption globally. OpenAI maintains technical leadership in AI while cooperating with global institutions to address AGI challenges. It seeks to lead a collaborative worldwide effort developing AGI for collective good."
eval_summary_2 = "OpenAI aims to ensure AGI is for everyone's use, totally avoiding harmful stuff or big power concentration. Committed to researching AGI's safe side, promoting these studies in AI folks. OpenAI wants to be top in AI things and works with worldwide research, policy groups to figure AGI's stuff."

# Evaluation prompt template based on G-Eval
EVALUATION_PROMPT_TEMPLATE = """
You will be given one summary written for an article. Your task is to rate the summary on one metric.
Please make sure you read and understand these instructions very carefully. 
Please keep this document open while reviewing, and refer to it as needed.

Evaluation Criteria:

{criteria}

Evaluation Steps:

{steps}

Source Text:

{document}

Summary:

{summary}

Evaluation Form (scores ONLY without any additional comments):

- {metric_name}
"""

# Metric 1: Relevance

RELEVANCY_SCORE_CRITERIA = """
Relevance(1-5) - selection of important content from the source. \
The summary should include only important information from the source document. \
Annotators were instructed to penalize summaries which contained redundancies and excess information.
"""

RELEVANCY_SCORE_STEPS = """
1. Read the summary and the source document carefully.
2. Compare the summary to the source document and identify the main points of the article.
3. Assess how well the summary covers the main points of the article, and how much irrelevant or redundant information it contains.
4. Assign a relevance score from 1 to 5.
"""

# Metric 2: Coherence

COHERENCE_SCORE_CRITERIA = """
Coherence(1-5) - the collective quality of all sentences. \
We align this dimension with the DUC quality question of structure and coherence \
whereby "the summary should be well-structured and well-organized. \
The summary should not just be a heap of related information, but should build from sentence to a\
coherent body of information about a topic."
"""

COHERENCE_SCORE_STEPS = """
1. Read the article carefully and identify the main topic and key points.
2. Read the summary and compare it to the article. Check if the summary covers the main topic and key points of the article,
and if it presents them in a clear and logical order.
3. Assign a score for coherence on a scale of 1 to 5, where 1 is the lowest and 5 is the highest based on the Evaluation Criteria.
"""

# Metric 3: Consistency

CONSISTENCY_SCORE_CRITERIA = """
Consistency(1-5) - the factual alignment between the summary and the summarized source. \
A factually consistent summary contains only statements that are entailed by the source document. \
Annotators were also asked to penalize summaries that contained hallucinated facts.
"""

CONSISTENCY_SCORE_STEPS = """
1. Read the article carefully and identify the main facts and details it presents.
2. Read the summary and compare it to the article. Check if the summary contains any factual errors that are not supported by the article.
3. Assign a score for consistency based on the Evaluation Criteria.
"""

# Metric 4: Fluency

FLUENCY_SCORE_CRITERIA = """
Fluency(1-3): the quality of the summary in terms of grammar, spelling, punctuation, word choice, and sentence structure.
1: Poor. The summary has many errors that make it hard to understand or sound unnatural.
2: Fair. The summary has some errors that affect the clarity or smoothness of the text, but the main points are still comprehensible.
3: Good. The summary has few or no errors and is easy to read and follow.
"""

FLUENCY_SCORE_STEPS = """
Read the summary and evaluate its fluency based on the given criteria. Assign a fluency score from 1 to 3.
"""


def create_client() -> openai.OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(
        api_key=api_key,
    )
    return client


def get_geval_score(criteria: str, steps: str, document: str, summary: str, metric_name: str):
    client = create_client()
    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        criteria=criteria,
        steps=steps,
        metric_name=metric_name,
        document=document,
        summary=summary,
    )
    print(prompt)
    response = client.chat.completions.create(
        # model="gpt-4o",
        # model="gpt-4",
        model="gpt-3.5-turbo-0125",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=50,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    return response.choices[0].message.content


evaluation_metrics = {
    "Relevance": (RELEVANCY_SCORE_CRITERIA, RELEVANCY_SCORE_STEPS),
    "Coherence": (COHERENCE_SCORE_CRITERIA, COHERENCE_SCORE_STEPS),
    "Consistency": (CONSISTENCY_SCORE_CRITERIA, CONSISTENCY_SCORE_STEPS),
    "Fluency": (FLUENCY_SCORE_CRITERIA, FLUENCY_SCORE_STEPS),
}

summaries = {
    "Summary Ref": ref_summary,
    "Summary 1": eval_summary_1,
    "Summary 2": eval_summary_2,
}
# summaries = {"Summary 1": eval_summary_1, "Summary 2": eval_summary_2}

data = {"Evaluation Type": [], "Summary Type": [], "Score": []}

for eval_type, (criteria, steps) in evaluation_metrics.items():
    for summ_type, summary in summaries.items():
        data["Evaluation Type"].append(eval_type)
        data["Summary Type"].append(summ_type)
        result = get_geval_score(criteria, steps, excerpt, summary, eval_type)
        score_num = int(result.strip())
        data["Score"].append(score_num)
# Convert data to DataFrame
df = pd.DataFrame(data)

# Pivot the DataFrame for better comparison
pivot_df = df.pivot(index="Evaluation Type", columns="Summary Type", values="Score").reset_index()

# Print the table using tabulate
print(tabulate(pivot_df, headers="keys", tablefmt="grid"))

# # Create a bar graph
# fig, ax = plt.subplots()
# bar_width = 0.15
# index = np.arange(len(pivot_df))

# summary_0_scores = pivot_df["Summary Ref"]
# summary_1_scores = pivot_df["Summary 1"]
# summary_2_scores = pivot_df["Summary 2"]

# bar0 = ax.bar(index, summary_0_scores, bar_width, label="Summary Ref")
# bar1 = ax.bar(index + bar_width, summary_1_scores, bar_width, label="Summary 1")
# bar2 = ax.bar(index + bar_width * 2, summary_2_scores, bar_width, label="Summary 2")

# ax.set_xlabel("Evaluation Type")
# ax.set_ylabel("Scores")
# ax.set_title("Comparison of Summary 1 and Summary 2 Scores")
# ax.set_xticks(index + bar_width / 2)
# ax.set_xticklabels(pivot_df["Evaluation Type"], rotation=45)
# ax.legend()

# plt.tight_layout()
# plt.show()
