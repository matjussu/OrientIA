"""Parallel dispatch helpers — Sprint 3 axe B agentique latency optims.

Adresse le caveat #1 Sprint 2 (latence end-to-end 22-29s projetée).
Permet d'exécuter N calls Mistral en parallèle (vs séquentiel) quand
les tasks sont indépendantes (ex: fact-check sur N sub-queries de
QueryReformuler).

## Choix d'implémentation : ThreadPoolExecutor

Le SDK `mistralai` a un client async (`Mistral.do_request_async`)
mais l'usage idiomatique reste synchrone (`client.chat.complete(...)`).
Pour Sprint 3 MVP, on wrap les calls sync avec
`concurrent.futures.ThreadPoolExecutor` — gain ~Nx sur les calls
indépendants, sans réécrire la stack en async/await.

Rationale :
- Mistral API est I/O bound (network) → threads suffisent (pas de GIL contention)
- Pas de réécriture de l'agent loop en async (complexe + risque régression)
- Pattern compatible Sprint 4 (batching multi-corpus retrieval)

## Pattern d'usage

```python
from src.agent.parallel import parallel_map

# Run N fact-checks en parallèle
def fact_check_one(claim):
    return fetch.verify(claim, sources)

results = parallel_map(fact_check_one, claims, max_workers=5)
# results = list[StatVerification], same order as claims
```

## Caveat

- Erreurs partielles : si 1 task throw, les autres complètent.
  `parallel_map` retourne soit la valeur, soit l'exception (caller décide).
- Rate limit Mistral peut hit avec >5 workers parallèles. Le retry
  intégré (Sprint 2 (4)) gère gracefully.
- Logging : pas de visibilité granulaire par task. Pour audit, le
  caller doit injecter son propre wrapper si nécessaire.
"""
from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T")
R = TypeVar("R")


def parallel_map(
    fn: Callable[[T], R],
    items: Iterable[T],
    *,
    max_workers: int = 5,
    timeout_per_item: float | None = None,
    return_exceptions: bool = False,
) -> list[R]:
    """Map `fn` sur `items` en parallèle, ordre préservé.

    Args:
        fn: callable qui prend un item et retourne un résultat. Doit
            être thread-safe (Mistral SDK calls le sont).
        items: itérable d'items à traiter.
        max_workers: nombre de threads workers (défaut 5). Au-delà,
            risque de hit rate limit Mistral.
        timeout_per_item: timeout en secondes par item. None = pas de
            timeout (attend indéfiniment).
        return_exceptions: si True, les exceptions sont retournées en
            place dans la liste (caller fait le tri). Si False (défaut),
            la première exception remonte et annule les autres.

    Returns:
        Liste de résultats dans le même ordre que `items` en entrée.

    Raises:
        Première exception rencontrée si `return_exceptions=False`.
    """
    items_list = list(items)
    if not items_list:
        return []
    if max_workers < 1:
        raise ValueError("max_workers doit être >= 1")

    # Limiter workers au nombre d'items (pas de threads inutiles)
    effective_workers = min(max_workers, len(items_list))

    results: list[Any] = [None] * len(items_list)
    with concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers) as executor:
        # Submit toutes les tasks avec leur index
        future_to_idx = {
            executor.submit(fn, item): idx
            for idx, item in enumerate(items_list)
        }
        for future in concurrent.futures.as_completed(future_to_idx, timeout=None):
            idx = future_to_idx[future]
            try:
                if timeout_per_item is not None:
                    results[idx] = future.result(timeout=timeout_per_item)
                else:
                    results[idx] = future.result()
            except Exception as exc:
                if return_exceptions:
                    results[idx] = exc
                else:
                    # Cancel pending futures pour fail-fast
                    for f in future_to_idx:
                        f.cancel()
                    raise
    return results


def parallel_apply(
    fn: Callable[..., R],
    args_list: Iterable[tuple],
    *,
    max_workers: int = 5,
    return_exceptions: bool = False,
) -> list[R]:
    """Variant : `fn(*args)` pour chaque tuple d'args. Ordre préservé.

    Pratique quand `fn` prend plusieurs args :
        results = parallel_apply(fetch.verify, [(claim1, sources1), (claim2, sources2)])
    """
    return parallel_map(
        lambda args: fn(*args),
        args_list,
        max_workers=max_workers,
        return_exceptions=return_exceptions,
    )
