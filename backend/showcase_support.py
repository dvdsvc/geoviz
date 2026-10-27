"""Showcase-only startup and offline keyword demonstration.

These helpers were added for packaging and are not historical RAG algorithms.
"""
import importlib


class LazyComponent:
    def __init__(self, module, name):
        self._module, self._name, self._instance = module, name, None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = getattr(importlib.import_module(self._module), self._name)()
        return getattr(self._instance, name)


def demo_chat(query, samples):
    text=query.strip().lower()
    if text in {'all','demo','全部','所有样品','合成数据'}:
        matched=list(samples)
    else:
        fields=('sampleId','basin','formation','rockType','datingMineral','regionProvince')
        matched=[s for s in samples if any(str(s.get(field,'')).lower() in text
                    for field in fields if s.get(field))]
    lines=[f"合成数据演示（本地关键词匹配）：找到 {len(matched)} 条记录。"]
    lines.extend(f"{s['sampleId']} · {s['rockType']} · {s['ageMa']} Ma" for s in matched)
    return {'answer':'\n'.join(lines),'samples':matched,'filters':{'mode':'synthetic-keyword-demo'}}
