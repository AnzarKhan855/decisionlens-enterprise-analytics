from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class DecisionModeRouter:
    """
    Decision Mode Router for the Enterprise Decision Engine.

    Classifies user questions into specific decision modes and
    determines the required pipeline stages.

    Supported modes:
      - explain
      - compare
      - predict
      - recommend
      - diagnose
      - summarize
      - root_cause_analysis
      - what_if_simulation
      - risk_assessment
      - opportunity_detection
      - benchmark
    """

    MODE_PATTERNS = {
        "explain": [
            r"explain\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)",
            r"what\s+does\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)\s+show",
            r"interpret\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)",
            r"why\s+is\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)",
            r"what\s+is\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)",
        ],
        "compare": [
            r"compare\s+\w+\s+(?:to|with|against|versus|\bvs\b)\s+\w+",
            r"compare\s+\w+\s+and\s+\w+",
            r"compare\s+\w+\s+by\s+\w+",
            r"comparison\b",
            r"versus\b",
            r"\bvs\b",
            r"difference\s+between\s+\w+\s+and\s+\w+",
            r"contrast\s+\w+\s+(?:to|with|against)\s+\w+",
            r"how\s+does\s+\w+\s+compare",
            r"which\s+is\s+(?:better|worse|higher|lower|faster|slower)",
        ],
        "predict": [
            r"forecast\b",
            r"predict\b",
            r"projection\b",
            r"future\s+\w+",
            r"next\s+\d+\s+(month|quarter|year|week|day)",
            r"expected\s+\w+",
            r"projected\s+\w+",
            r"will\s+\w+",
            r"what\s+will\s+happen",
            r"what\s+is\s+the\s+forecast",
            r"what\s+do\s+you\s+expect",
            r"outlook\b",
            r"trajectory\b",
        ],
        "recommend": [
            r"recommend\b",
            r"recommendation\b",
            r"suggest\b",
            r"should\s+\w+",
            r"advise\b",
            r"what\s+should\s+\w+",
            r"action\s+item\b",
            r"next\s+step\b",
            r"how\s+should\s+we\s+\w+",
            r"what\s+would\s+you\s+do",
            r"best\s+course\s+of\s+action",
            r"how\s+to\s+improve\b",
            r"what\s+should\s+(?:management|we|leadership)\s+do",
        ],
        "diagnose": [
            r"diagnose\b",
            r"^why\b",
            r"why\?",
            r"why\s+is\s+that",
            r"why\s+is\s+\w+\s+(?:low|high|dropping|falling|rising|spiking|declining|increasing)",
            r"what\s+caused\s+\w+",
            r"root\s+cause\b",
            r"reason\s+for\b",
            r"reason\s+behind\b",
            r"why\s+is\s+this\s+happening",
            r"what\s+happened\s+to\b",
            r"why\s+did\s+\w+\s+(?:change|increase|decrease|drop|spike)",
            r"what\s+is\s+driving\b",
            r"what\s+factors?\s+(?:affect|impact|drive|influence)\b",
        ],
        "root_cause_analysis": [
            r"root\s+cause\s+analysis\b",
            r"analyze\s+root\s+cause\b",
            r"identify\s+root\s+cause\b",
            r"find\s+root\s+cause\b",
            r"^why\b",
            r"why\?",
            r"why\s+is\s+\w+\s+(?:low|high|dropping|falling|rising|spiking|declining|increasing)",
            r"what\s+is\s+causing\s+\w+",
            r"what\s+drives?\s+\w+",
        ],
        "what_if_simulation": [
            r"what\s+if\b",
            r"what-if\b",
            r"scenario\b",
            r"simulate\b",
            r"simulation\b",
            r"if\s+\w+\s+(?:increases|decreases|changes|drops|rises)\s+by\s+\d+",
            r"assuming\s+\w+\s+is\s+\d+",
            r"hypothetical\b",
            r"suppose\s+\w+",
            r"if\s+we\s+(?:increase|decrease|change|reduce|raise)\s+\w+",
            r"what\s+happens\s+if\b",
            r"increase\s+\w+\s+by\s+\d+",
            r"decrease\s+\w+\s+by\s+\d+",
        ],
        "risk_assessment": [
            r"risk\s+assessment\b",
            r"assess\s+risk\b",
            r"evaluate\s+risk\b",
            r"what\s+are\s+the\s+risks\b",
            r"risk\s+analysis\b",
            r"identify\s+risks\b",
            r"potential\s+risks\b",
            r"threats?\b",
            r"assess\s+business\s+risks\b",
            r"business\s+risk\s+assessment\b",
        ],
        "opportunity_detection": [
            r"opportunity\s+detection\b",
            r"detect\s+opportunit",
            r"find\s+opportunit",
            r"identify\s+opportunit",
            r"growth\s+opportunit",
            r"what\s+are\s+the\s+opportunities",
            r"where\s+can\s+we\s+grow",
            r"areas?\s+for\s+growth",
            r"potential\s+gains?\b",
            r"upside\b",
        ],
        "benchmark": [
            r"benchmark\b",
            r"compare\s+(?:against|to)\s+previous\b",
            r"compare\s+(?:against|to)\s+last\s+(?:month|quarter|year|period)",
            r"how\s+are\s+we\s+performing\s+(?:against|vs|versus)\b",
            r"performance\s+(?:against|vs|versus)\b",
            r"how\s+does\s+this\s+compare\s+to\s+previous",
            r"trend\s+over\s+time\b",
            r"progress\s+over\s+time\b",
            r"year\s+over\s+year\b",
            r"month\s+over\s+month\b",
            r"qoq\b",
            r"mom\b",
            r"yoy\b",
        ],
        "summarize": [
            r"summarize\b",
            r"summary\b",
            r"overview\b",
            r"executive\s+summary\b",
            r"brief\s+me\s+on\b",
            r"give\s+me\s+a\s+summary",
            r"provide\s+an?\s+overview",
            r"what\s+does\s+the\s+data\s+say",
            r"tell\s+me\s+about\s+the\s+data",
            r"what\s+are\s+the\s+key\s+points",
        ],
    }

    @classmethod
    def route(cls, question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        q = question.lower().strip()
        scores: Dict[str, float] = {}

        follow_up_indicators = [
            "why", "why is that", "why is it", "why are they", "how come",
            "what about", "which one", "what else", "explain more", "elaborate",
            "tell me more", "go on", "and then", "what happened", "what caused",
            "what should i do", "what should we do", "is that risky", "is it risky",
            "compare them", "compare those", "compare the", "show me more",
            "what happens next", "what if i change", "what if we change",
            "what if", "summarize everything", "summarise everything",
            "what happens if",
        ]

        is_follow_up = any(q.startswith(p) or q == p for p in follow_up_indicators)

        if is_follow_up and history:
            last_user = next((t["content"].lower() for t in reversed(history) if t.get("role") == "user"), "")
            last_assistant = next((t["content"].lower() for t in reversed(history) if t.get("role") == "assistant"), "")

            combined_text = last_user + " " + last_assistant

            for mode, patterns in cls.MODE_PATTERNS.items():
                score = 0.0
                for pattern in patterns:
                    matches = re.findall(pattern, combined_text)
                    if matches:
                        score += len(matches) * 1.5
                scores[mode] = score

            if q.startswith("why") or q.startswith("why is that") or q.startswith("why is it"):
                scores["root_cause_analysis"] = scores.get("root_cause_analysis", 0.0) + 5.0
                scores["diagnose"] = scores.get("diagnose", 0.0) + 4.0
            elif q.startswith("what should") or q.startswith("what would you do"):
                scores["recommend"] = scores.get("recommend", 0.0) + 5.0
            elif q.startswith("what if") or q.startswith("what happens if"):
                scores["what_if_simulation"] = scores.get("what_if_simulation", 0.0) + 5.0
            elif q.startswith("compare"):
                scores["compare"] = scores.get("compare", 0.0) + 5.0
            elif q.startswith("is that risky") or q.startswith("is it risky"):
                scores["risk_assessment"] = scores.get("risk_assessment", 0.0) + 5.0
            elif q.startswith("what happens next"):
                scores["predict"] = scores.get("predict", 0.0) + 5.0
            elif q.startswith("summarize everything") or q.startswith("summarise everything"):
                scores["summarize"] = scores.get("summarize", 0.0) + 5.0
        else:
            for mode, patterns in cls.MODE_PATTERNS.items():
                score = 0.0
                for pattern in patterns:
                    matches = re.findall(pattern, q)
                    if matches:
                        score += len(matches) * 1.0
                scores[mode] = score

            if history:
                last_user = next((t["content"].lower() for t in reversed(history) if t.get("role") == "user"), "")
                if last_user:
                    for mode, patterns in cls.MODE_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, last_user):
                                scores[mode] = scores.get(mode, 0.0) + 0.2

        best_mode = max(scores, key=lambda k: scores[k]) if scores else "summarize"
        if scores.get(best_mode, 0.0) == 0.0:
            best_mode = "summarize"

        max_score = max(scores.values()) if scores else 0.0
        confidence = min(0.98, 0.55 + (max_score * 0.15)) if max_score > 0 else 0.55

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return {
            "mode": best_mode,
            "confidence": round(confidence, 2),
            "all_scores": dict(sorted_scores),
            "requires_analytics": cls._requires_analytics(best_mode),
            "requires_prediction": best_mode in ("predict", "forecast", "what_if_simulation", "benchmark"),
            "requires_recommendation": best_mode in ("recommend", "diagnose", "root_cause_analysis", "risk_assessment"),
            "requires_report": best_mode in ("summarize", "explain", "benchmark"),
            "requires_memory": True,
            "requires_context": True,
            "is_follow_up": is_follow_up if history else None,
        }

    @classmethod
    def _requires_analytics(cls, mode: str) -> bool:
        return mode not in ("explain",)

    @classmethod
    def get_mode_description(cls, mode: str) -> str:
        descriptions = {
            "explain": "Explain a visualization, report, or finding",
            "compare": "Compare entities, segments, or time periods",
            "predict": "Forecast future values or trends",
            "recommend": "Generate evidence-based recommendations",
            "diagnose": "Diagnose issues or changes in metrics",
            "summarize": "Provide an executive summary",
            "root_cause_analysis": "Identify root causes of business changes",
            "what_if_simulation": "Simulate hypothetical scenarios",
            "risk_assessment": "Assess business risks",
            "opportunity_detection": "Detect growth opportunities",
            "benchmark": "Benchmark performance over time or against targets",
        }
        return descriptions.get(mode, "General analysis")
