"""src/experimental/ — modules POC ou variants non-branchés au pipeline production.

Distinction claire avec src/rag/, src/eval/ etc. : ces modules sont conservés
pour leur valeur (méthodologie publiée, options d'override, briques d'infra
futures), mais ils ne tournent PAS dans le pipeline runtime de make_production_pipeline().

Modules présents :
- system_strict : variant SYSTEM_PROMPT v3.3 (additif anti-hallu strict, R1-R6)
- critic_loop  : pattern 2-pass LLM relecture (Sprint 7 Action 3, reverté Sprint 8 R3)
- multi_corpus : loader unifié 4+ corpus retrievables (formation + métier + APEC + parcours)
- judge_v2/    : méthodologie Phase G fact-check reweight (méthodologie publication)

Pour toute promotion d'un module vers production : ouvrir un ADR + créer un PR
qui (a) bouge le module hors experimental, (b) le branche dans la factory, (c)
mesure le delta sur mini-bench.
"""
