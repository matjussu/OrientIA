# ============================================================
# Script 03 : Tests bivariés et corrélations
# Projet : OrientIA
# ------------------------------------------------------------
# Suit le plan d'analyse à 3 niveaux :
#   1. Qualité du conseil  ->  Réorientation
#   2. Origine sociale/géographique  ->  Qualité du conseil
#   3. Usage de l'IA  ->  Information perçue
# ============================================================

# Encoding UTF-8 (essai fr_FR puis fallback C.UTF-8 si indisponible).
# Sans ce fallback, sur une machine sans fr_FR.UTF-8 les case_when avec
# chaînes accentuées échouent silencieusement et les tests sortent faux.
suppressWarnings({
  res <- Sys.setlocale("LC_ALL", "fr_FR.UTF-8")
  if (res == "") Sys.setlocale("LC_ALL", "C.UTF-8")
})

library(dplyr)

df <- readRDS("data/donnees_pilote_propres.rds")

section <- function(titre) {
  cat("\n\n=============================================================\n")
  cat(titre, "\n")
  cat("=============================================================\n")
}

likert_vars <- c("info_percue", "conseil_adapte", "preparation_emploi")

# ------------------------------------------------------------
# 0. CORRÉLATIONS DE BASE ENTRE VARIABLES LIKERT (Spearman)
# ------------------------------------------------------------
section("0. CORRÉLATIONS SPEARMAN ENTRE VARIABLES LIKERT")

mat_cor <- cor(df[, likert_vars], method = "spearman", use = "pairwise.complete.obs")
print(round(mat_cor, 3))

cat("\nTests de significativité (Spearman) :\n")
combos <- combn(likert_vars, 2, simplify = FALSE)
for (paire in combos) {
  res <- suppressWarnings(cor.test(df[[paire[1]]], df[[paire[2]]], method = "spearman"))
  cat(sprintf("  %s vs %s : rho = %.3f, p = %.4f\n",
              paire[1], paire[2], res$estimate, res$p.value))
}

# ------------------------------------------------------------
# NIVEAU 1 : QUALITÉ DU CONSEIL  ->  RÉORIENTATION
# ------------------------------------------------------------
section("NIVEAU 1 : QUALITÉ DU CONSEIL -> RÉORIENTATION")

cat("\n--- 1.1 Conseil adapté vs Statut de réorientation ---\n")
test1 <- wilcox.test(conseil_adapte ~ reoriente_bin, data = df)
moy_par_groupe <- df %>%
  group_by(reoriente_bin) %>%
  summarise(n = n(),
            moy_conseil = round(mean(conseil_adapte, na.rm = TRUE), 2),
            med_conseil = median(conseil_adapte, na.rm = TRUE),
            .groups = "drop")
print(moy_par_groupe)
cat(sprintf("Mann-Whitney U : W = %.0f, p = %.4f\n", test1$statistic, test1$p.value))

cat("\n--- 1.2 Information perçue vs Statut de réorientation ---\n")
test2 <- wilcox.test(info_percue ~ reoriente_bin, data = df)
moy_info <- df %>%
  group_by(reoriente_bin) %>%
  summarise(n = n(),
            moy_info = round(mean(info_percue, na.rm = TRUE), 2),
            med_info = median(info_percue, na.rm = TRUE),
            .groups = "drop")
print(moy_info)
cat(sprintf("Mann-Whitney U : W = %.0f, p = %.4f\n", test2$statistic, test2$p.value))

cat("\n--- 1.3 Regret (Q16.3) ~ Conseil adapté (Q14), parmi les réorientés ---\n")
df_r <- df %>% filter(reoriente_bin == 1)
test3 <- suppressWarnings(
  cor.test(df_r$regret_reorientation, df_r$conseil_adapte, method = "spearman")
)
cat(sprintf("Spearman rho = %.3f, p = %.4f, N = %d\n",
            test3$estimate, test3$p.value,
            sum(complete.cases(df_r[, c("regret_reorientation","conseil_adapte")]))))

# ------------------------------------------------------------
# NIVEAU 2 : ORIGINE SOCIALE/GÉOGRAPHIQUE -> QUALITÉ DU CONSEIL
# ------------------------------------------------------------
section("NIVEAU 2 : ORIGINE -> QUALITÉ DU CONSEIL")

test_kw <- function(formule, donnees, label) {
  cat("\n--- ", label, " ---\n", sep = "")
  res <- kruskal.test(formule, data = donnees)
  vars <- all.vars(formule)
  agg <- donnees %>%
    group_by(.data[[vars[2]]]) %>%
    summarise(n = n(),
              moy = round(mean(.data[[vars[1]]], na.rm = TRUE), 2),
              med = median(.data[[vars[1]]], na.rm = TRUE),
              .groups = "drop")
  print(agg)
  cat(sprintf("Kruskal-Wallis : H = %.2f, df = %d, p = %.4f\n",
              res$statistic, res$parameter, res$p.value))
}

# 2.1 — IMPORTANT : on restreint aux 5 catégories interprétables.
# "Autre" (n=3) et "Préfère ne pas répondre" (n=1) sont exclus car
# leur contenu ne correspond pas à un niveau d'études identifiable,
# et leurs très faibles effectifs déstabilisent le test.
# Ce filtrage est ce qui produit H = 6,38 ; df = 4 ; p = 0,173 (N=176).
df_niveau_parents_5cat <- df %>%
  filter(niveau_parents %in% c(
    "Aucun diplôme / Brevet",
    "CAP / BEP",
    "Baccalauréat",
    "Bac+2 / Bac+3",
    "Bac+5 et plus"
  ))

test_kw(conseil_adapte ~ niveau_parents, df_niveau_parents_5cat,
        sprintf("2.1 Conseil adapté ~ Niveau d'études des parents (5 catégories interprétables, N=%d)",
                nrow(df_niveau_parents_5cat)))

test_kw(conseil_adapte ~ type_commune, df,
        "2.2 Conseil adapté ~ Type de commune (lycée)")
test_kw(conseil_adapte ~ type_bac, df,
        "2.3 Conseil adapté ~ Type de bac")
test_kw(info_percue ~ niveau_parents, df_niveau_parents_5cat,
        sprintf("2.4 Information perçue ~ Niveau d'études des parents (5 catégories, N=%d)",
                nrow(df_niveau_parents_5cat)))
test_kw(info_percue ~ type_commune, df,
        "2.5 Information perçue ~ Type de commune")

# ------------------------------------------------------------
# NIVEAU 3 : USAGE DE L'IA -> INFORMATION PERÇUE
# ------------------------------------------------------------
section("NIVEAU 3 : USAGE DE L'IA -> INFORMATION PERÇUE")

cat("\n--- 3.1 Information perçue ~ IA pour le choix de formation ---\n")
moy_ia <- df %>%
  group_by(ia_formation) %>%
  summarise(n = n(),
            moy = round(mean(info_percue, na.rm = TRUE), 2),
            med = median(info_percue, na.rm = TRUE),
            .groups = "drop")
print(moy_ia)
test_ia1 <- kruskal.test(info_percue ~ ia_formation, data = df)
cat(sprintf("Kruskal-Wallis : H = %.2f, df = %d, p = %.4f\n",
            test_ia1$statistic, test_ia1$parameter, test_ia1$p.value))

cat("\n--- 3.2 Information perçue ~ IA pour exploration des métiers ---\n")
moy_ia2 <- df %>%
  group_by(ia_metiers) %>%
  summarise(n = n(),
            moy = round(mean(info_percue, na.rm = TRUE), 2),
            med = median(info_percue, na.rm = TRUE),
            .groups = "drop")
print(moy_ia2)
test_ia2 <- kruskal.test(info_percue ~ ia_metiers, data = df)
cat(sprintf("Kruskal-Wallis : H = %.2f, df = %d, p = %.4f\n",
            test_ia2$statistic, test_ia2$parameter, test_ia2$p.value))

cat("\n--- 3.3 Version binaire (utilise vs n'utilise pas) ---\n")
test_b1 <- wilcox.test(info_percue ~ ia_formation_bin, data = df)
cat(sprintf("IA formation (bin) : W = %.0f, p = %.4f\n",
            test_b1$statistic, test_b1$p.value))
test_b2 <- wilcox.test(info_percue ~ ia_metiers_bin, data = df)
cat(sprintf("IA métiers   (bin) : W = %.0f, p = %.4f\n",
            test_b2$statistic, test_b2$p.value))

# ------------------------------------------------------------
# CROISEMENTS COMPLÉMENTAIRES
# ------------------------------------------------------------
section("CROISEMENTS COMPLÉMENTAIRES")

cat("\n--- 4.1 Réorientation par filière ---\n")
tab_fil <- with(df, table(filiere, reoriente_bin, useNA = "no"))
print(tab_fil)
chi_fil <- suppressWarnings(chisq.test(tab_fil))
cat(sprintf("Chi-2 : X-squared = %.2f, df = %d, p = %.4f\n",
            chi_fil$statistic, chi_fil$parameter, chi_fil$p.value))
# Plusieurs cellules ont une fréquence attendue < 5, le chi-2 sort un
# warning. Fisher exact en Monte-Carlo est plus fiable et c'est la valeur
# citée dans le rapport (Section 3.4.3 : "p = 0.010").
fisher_fil <- fisher.test(tab_fil, simulate.p.value = TRUE, B = 10000)
cat(sprintf("Fisher exact (Monte-Carlo, B=10000) : p = %.4f\n", fisher_fil$p.value))

cat("\n--- 4.2 Réorientation par fréquence de visite au PsyEN ---\n")
tab_psy <- with(df, table(frequence_psyen, reoriente_bin, useNA = "no"))
print(tab_psy)
chi_psy <- suppressWarnings(chisq.test(tab_psy))
cat(sprintf("Chi-2 : X-squared = %.2f, df = %d, p = %.4f\n",
            chi_psy$statistic, chi_psy$parameter, chi_psy$p.value))

cat("\n--- 4.3 Usage de l'IA (formation) selon niveau parents ---\n")
tab_ia <- with(df, table(niveau_parents, ia_formation_bin, useNA = "no"))
print(tab_ia)
chi_ia <- suppressWarnings(chisq.test(tab_ia))
cat(sprintf("Chi-2 : X-squared = %.2f, df = %d, p = %.4f\n",
            chi_ia$statistic, chi_ia$parameter, chi_ia$p.value))

# ------------------------------------------------------------
# 4.4 NOUVEAUX TESTS : reproduction sociale et accès au PsyEN
# ------------------------------------------------------------
# Préparation des variables regroupées (mêmes définitions que script 04)
df_test <- df %>%
  mutate(
    niveau_parents_grp = case_when(
      niveau_parents %in% c("Aucun diplôme / Brevet", "CAP / BEP") ~ "Faible",
      niveau_parents %in% c("Baccalauréat", "Bac+2 / Bac+3")       ~ "Intermédiaire",
      niveau_parents == "Bac+5 et plus"                             ~ "Supérieur",
      TRUE ~ NA_character_
    ),
    filiere_grp = case_when(
      filiere %in% c("École de commerce / management", "École d'ingénieurs",
                     "École d'art / design / architecture",
                     "Santé (médecine, pharmacie, kiné, infirmier…)") ~ "Sélective",
      filiere %in% c("Économie / Gestion / Commerce",
                     "Droit / Science politique") ~ "Univ. éco/droit",
      filiere %in% c("Lettres / Sciences humaines / Sciences sociales",
                     "Sciences / Mathématiques / Informatique") ~ "Univ. généraliste",
      TRUE ~ NA_character_
    ),
    psyen_bin_lab = if_else(frequence_psyen == "Jamais",
                            "Jamais vu", "Au moins 1 fois")
  )

cat("\n--- 4.4 Niveau parents x Filière (reproduction sociale) ---\n")
tab_pf <- with(df_test, table(niveau_parents_grp, filiere_grp))
print(tab_pf)
cat("\nProportions par ligne (en %) :\n")
print(round(100 * prop.table(tab_pf, margin = 1), 1))
chi_pf <- suppressWarnings(chisq.test(tab_pf))
cat(sprintf("\nChi-2 : X-squared = %.2f, df = %d, p = %.4f\n",
            chi_pf$statistic, chi_pf$parameter, chi_pf$p.value))
# Test exact de Fisher en complément (plus robuste si effectifs faibles)
fisher_pf <- suppressWarnings(fisher.test(tab_pf, simulate.p.value = TRUE, B = 10000))
cat(sprintf("Fisher exact (Monte-Carlo) : p = %.4f\n", fisher_pf$p.value))

cat("\n--- 4.5 Niveau parents x Accès au PsyEN (égalité du service public) ---\n")
tab_psy_p <- with(df_test, table(niveau_parents_grp, psyen_bin_lab))
print(tab_psy_p)
cat("\nProportions par ligne (en %) :\n")
print(round(100 * prop.table(tab_psy_p, margin = 1), 1))
chi_psy_p <- suppressWarnings(chisq.test(tab_psy_p))
cat(sprintf("\nChi-2 : X-squared = %.2f, df = %d, p = %.4f\n",
            chi_psy_p$statistic, chi_psy_p$parameter, chi_psy_p$p.value))

cat("\n=============================================================\n")
cat("FIN DES TESTS BIVARIÉS\n")
cat("=============================================================\n")
