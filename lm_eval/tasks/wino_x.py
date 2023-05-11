"""
Wino-X: Multilingual Winograd Schemas for Commonsense Reasoning and Coreference Resolution
https://aclanthology.org/2021.emnlp-main.670.pdf

Winograd schemas are a well-established tool for evaluating coreference resolution (CoR)
and commonsense reasoning (CSR) capabilities of computational models. So far, schemas
remained largely confined to English, limiting their utility in multilingual settings. This work
presents Wino-X, a parallel dataset of German, French, and Russian schemas, aligned
with their English counterparts. This is a translated dataset from Winogrande. WinoGrande is a collection of 44k problems, inspired by Winograd Schema Challenge
(Levesque, Davis, and Morgenstern 2011), but adjusted to improve the scale and
robustness against the dataset-specific bias. Formulated as a fill-in-a-blank
task with binary options, the goal is to choose the right option for a given
sentence which requires commonsense reasoning.

See: https://aclanthology.org/2021.emnlp-main.670.pdf

"""
import numpy as np
from lm_eval.base import rf, Task
from lm_eval.metrics import mean


_CITATION = """
@inproceedings{emelin-sennrich-2021-wino,
    title = "Wino-{X}: Multilingual {W}inograd Schemas for Commonsense Reasoning and Coreference Resolution",
    author = "Emelin, Denis  and
      Sennrich, Rico",
    booktitle = "Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2021",
    address = "Online and Punta Cana, Dominican Republic",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.emnlp-main.670",
    doi = "10.18653/v1/2021.emnlp-main.670",
    pages = "8517--8532",
    abstract = "Winograd schemas are a well-established tool for evaluating coreference resolution (CoR) and commonsense reasoning (CSR) capabilities of computational models. So far, schemas remained largely confined to English, limiting their utility in multilingual settings. This work presents Wino-X, a parallel dataset of German, French, and Russian schemas, aligned with their English counterparts. We use this resource to investigate whether neural machine translation (NMT) models can perform CoR that requires commonsense knowledge and whether multilingual language models (MLLMs) are capable of CSR across multiple languages. Our findings show Wino-X to be exceptionally challenging for NMT systems that are prone to undesirable biases and unable to detect disambiguating information. We quantify biases using established statistical methods and define ways to address both of these issues. We furthermore present evidence of active cross-lingual knowledge transfer in MLLMs, whereby fine-tuning models on English schemas yields CSR improvements in other languages.",
}
"""


class WinograndeXDe(Task):
    VERSION = 0
    DATASET_PATH = "demelin/wino_x"
    DATASET_NAME = "lm_en_de"

    answer_to_num = {1: 0, 2: 1}

    def has_training_docs(self):
        return False

    def has_validation_docs(self):
        return False

    def has_test_docs(self):
        return True

    def training_docs(self):
        if self._training_docs is None:
            self._training_docs = list(self.dataset["train"])
        return self._training_docs

    def test_docs(self):
        return self.dataset["test"]

    def doc_to_text(self, doc):
        return self.partial_context(doc, doc["option" + str(doc["answer"]) + "_de"])

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["context_de"]

    @classmethod
    def partial_context(cls, doc, option):
        # Substitute the pronoun in the sentence with the specified option
        # and ignore everything after.
        pronoun_loc = doc["context_de"].index("_")
        return doc["context_de"][:pronoun_loc] + option

    def doc_to_target(self, doc):
        return self.partial_target(doc)

    @classmethod
    def partial_target(cls, doc):
        # The target is everything after the document specified pronoun.
        pronoun_loc = doc["context_de"].index("_") + 1
        return " " + doc["context_de"][pronoun_loc:].strip()

    def construct_requests(self, doc, ctx):
        """Uses RequestFactory to construct Requests and returns an iterable of
        Requests which will be sent to the LM.

        :param doc:
            The document as returned from training_docs, validation_docs, or test_docs.
        :param ctx: str
            The context string, generated by fewshot_context. This includes the natural
            language description, as well as the few shot examples, and the question
            part of the document for `doc`.
        """
        target = self.partial_target(doc)
        lls = []
        for option in [doc["option1_de"], doc["option2_de"]]:
            partial_ctx = self.partial_context(doc, option)
            full_ctx = self.append_context(ctx, partial_ctx)
            lls.append(rf.loglikelihood(full_ctx, target)[0])
        return lls

    @classmethod
    def append_context(cls, ctx, partial_ctx):
        ctx = ctx.split("\n\n")  # Each fewshot context is on its own new line.
        ctx.pop()  # Remove the correct context put in by `doc_to_text`.
        return "\n\n".join([*ctx, partial_ctx]) if ctx else partial_ctx

    def process_results(self, doc, results):
        """Take a single document and the LM results and evaluates, returning a
        dict where keys are the names of submetrics and values are the values of
        the metric for that one document

        :param doc:
            The document as returned from training_docs, validation_docs, or test_docs.
        :param results:
            The results of the requests created in construct_requests.
        """
        return {"acc": np.argmax(results) == self.answer_to_num[doc["answer"]]}

    def aggregation(self):
        """
        :returns: {str: [float] -> float}
            A dictionary where keys are the names of submetrics and values are
            functions that aggregate a list of metrics
        """
        return {"acc": mean}

    def higher_is_better(self):
        """
        :returns: {str: bool}
            A dictionary where keys are the names of submetrics and values are
            whether a higher value of the submetric is better
        """
        return {"acc": True}
