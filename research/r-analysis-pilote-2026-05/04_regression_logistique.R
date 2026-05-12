# ============================================================
# Script 04 : Régression logistique avec VIF
# Projet : OrientIA
# ------------------------------------------------------------
# Variable dépendante : reoriente_bin (s'est réorienté(e) ou non)
# Stratégie : modèle progressif en 3 étapes
#   Modèle 1 : qualité du conseil seule
#   Modèle 2 : ajout des variables sociodémographiques
#   Modèle 3 : modèle complet avec usage de l'IA
# Multicolinéarité contrôlée par VIF (seuil 5)
# ------------------------------------------------------------
# NB : "préparation à l'emploi" (Q15) est volontairement exclue
# du modèle (cf. plan d'analyse). Elle reste exploitable en
# descriptif et corrélations.
# ============================================================

# Encoding UTF-8 (essai fr_FR puis fallback C.UTF-8 si indisponible).
# Critique pour ce script : sans la bonne locale, les case_when avec
# chaînes accentuées échouent silencieusement et le Modèle 2 plante
# (filiere_grp / commune_grp / niveau_parents_grp se retrouvent vides).
suppressWarnings({
  res <- Sys.setlocale("LC_ALL", "fr_FR.UTF-8")
  if (res == "") Sys.setlocale("LC_ALL", "C.UTF-8")
})

library(dplyr)
library(car)

df <- readRDS("data/donnees_pilote_propres.rds")

# ------------------------------------------------------------
# 1. PRÉPARATION DES VARIABLES
# ------------------------------------------------------------
# Pour respecter la règle de Peduzzi (~10 cas par paramètre)
# avec 53 réorientés, on regroupe certaines variables catégorielles.

df <- df %>%
  mutate(

    # Niveau parents : 3 catégories
    niveau_parents_grp = case_when(
      niveau_parents %in% c("Aucun diplôme / Brevet", "CAP / BEP") ~ "Faible",
      niveau_parents %in% c("Baccalauréat", "Bac+2 / Bac+3") ~ "Intermédiaire",
      niveau_parents == "Bac+5 et plus" ~ "Supérieur",
      TRUE ~ NA_character_
    ),
    niveau_parents_grp = factor(niveau_parents_grp,
                                levels = c("Faible", "Intermédiaire", "Supérieur")),

    # Type commune : 3 catégories
    commune_grp = case_when(
      type_commune %in% c("Commune rurale (moins de 2 000 hab.)",
                          "Petite ville (2 000 – 20 000 hab.)") ~ "Rural / Petite",
      type_commune == "Ville moyenne (20 000 – 200 000 hab.)" ~ "Moyenne",
      type_commune %in% c("Grande ville / Métropole", "Paris intramuros") ~ "Grande / Paris",
      type_commune == "À l'étranger" ~ "Étranger",
      TRUE ~ NA_character_
    ),
    commune_grp = factor(commune_grp,
                         levels = c("Rural / Petite", "Moyenne", "Grande / Paris", "Étranger")),

    # Filière : 3 catégories pédagogiques
    filiere_grp = case_when(
      filiere %in% c("École de commerce / management", "École d'ingénieurs",
                     "École d'art / design / architecture",
                     "Santé (médecine, pharmacie, kiné, infirmier…)") ~ "Sélective",
      filiere %in% c("Économie / Gestion / Commerce", "Droit / Science politique") ~ "Univ. éco/droit",
      filiere %in% c("Lettres / Sciences humaines / Sciences sociales",
                     "Sciences / Mathématiques / Informatique") ~ "Univ. généraliste",
      TRUE ~ NA_character_
    ),
    filiere_grp = factor(filiere_grp,
                         levels = c("Sélective", "Univ. éco/droit", "Univ. généraliste")),

    # PsyEN : binaire (jamais vu vs au moins une fois)
    psyen_bin = case_when(
      frequence_psyen == "Jamais" ~ 0L,
      frequence_psyen %in% c("1 fois", "2 à 3 fois", "Plus de 3 fois") ~ 1L,
      TRUE ~ NA_integer_
    ),

    # Genre binaire (Femme = 1, Homme = 0, Non binaire exclu pour la régression)
    genre_bin = case_when(
      genre == "Femme" ~ 1L,
      genre == "Homme" ~ 0L,
      TRUE ~ NA_integer_
    )
  )

cat("Distribution des variables regroupées pour la régression :\n")
cat("\n--- niveau_parents_grp ---\n"); print(table(df$niveau_parents_grp, useNA = "ifany"))
cat("\n--- commune_grp ---\n");        print(table(df$commune_grp, useNA = "ifany"))
cat("\n--- filiere_grp ---\n");         print(table(df$filiere_grp, useNA = "ifany"))

# Garde-fou : on vérifie qu'aucune des variables regroupées n'a un niveau
# entièrement vide (signe que la locale a échoué et que les chaînes
# accentuées du case_when n'ont pas matché les données).
for (vname in c("niveau_parents_grp", "commune_grp", "filiere_grp")) {
  tab <- table(df[[vname]])
  if (any(tab == 0)) {
    stop(sprintf(
      "Variable %s : un ou plusieurs niveaux du facteur sont vides. ",
      vname),
      "Cela indique que les chaînes accentuées du case_when n'ont pas matché ",
      "les données — vérifier la locale (Sys.getlocale()) et l'encoding du fichier."
    )
  }
}

# ------------------------------------------------------------
# 2. MODÈLE 1 : QUALITÉ DU CONSEIL SEULE
# ------------------------------------------------------------
cat("\n\n=============================================================\n")
cat("MODÈLE 1 : reorientation ~ conseil_adapte + info_percue\n")
cat("=============================================================\n")

m1 <- glm(reoriente_bin ~ conseil_adapte + info_percue,
          data = df, family = binomial(link = "logit"))
print(summary(m1))

cat("\nOdds ratios + IC 95% :\n")
or1 <- exp(cbind(OR = coef(m1), confint.default(m1)))
print(round(or1, 3))

# ------------------------------------------------------------
# 3. MODÈLE 2 : AJOUT DES VARIABLES SOCIODÉMOGRAPHIQUES
# ------------------------------------------------------------
cat("\n\n=============================================================\n")
cat("MODÈLE 2 : + genre + niveau parents + commune + filière + PsyEN\n")
cat("=============================================================\n")

m2 <- glm(reoriente_bin ~ conseil_adapte + info_percue +
            genre_bin + niveau_parents_grp + commune_grp +
            filiere_grp + psyen_bin,
          data = df, family = binomial(link = "logit"))
print(summary(m2))

cat("\nOdds ratios + IC 95% :\n")
or2 <- exp(cbind(OR = coef(m2), confint.default(m2)))
print(round(or2, 3))

# ------------------------------------------------------------
# 4. MODÈLE 3 : COMPLET AVEC USAGE DE L'IA
# ------------------------------------------------------------
cat("\n\n=============================================================\n")
cat("MODÈLE 3 : modèle complet (avec usage IA)\n")
cat("=============================================================\n")

m3 <- glm(reoriente_bin ~ conseil_adapte + info_percue +
            genre_bin + niveau_parents_grp + commune_grp +
            filiere_grp + psyen_bin +
            ia_formation_bin + ia_metiers_bin,
          data = df, family = binomial(link = "logit"))
print(summary(m3))

cat("\nOdds ratios + IC 95% :\n")
or3 <- exp(cbind(OR = coef(m3), confint.default(m3)))
print(round(or3, 3))

# ------------------------------------------------------------
# 5. VIF - DIAGNOSTIC DE MULTICOLINÉARITÉ
# ------------------------------------------------------------
cat("\n\n=============================================================\n")
cat("VIF SUR LE MODÈLE COMPLET (seuil de vigilance : 5)\n")
cat("=============================================================\n")

vif_m3 <- vif(m3)
print(round(vif_m3, 3))

# Interprétation auto
if (is.matrix(vif_m3)) {
  gvif_adj <- vif_m3[, "GVIF^(1/(2*Df))"]
  vif_max <- max(gvif_adj)^2
} else {
  vif_max <- max(vif_m3)
}
cat(sprintf("\nVIF maximum : %.2f\n", vif_max))
if (vif_max > 5) {
  cat("ATTENTION : multicolinéarité notable, examiner les variables concernées.\n")
} else {
  cat("Pas de problème de multicolinéarité (toutes les VIF < 5).\n")
}

# ------------------------------------------------------------
# 6. ÉCHANTILLON COMMUN POUR COMPARAISON DES MODÈLES
# ------------------------------------------------------------
# Les LR tests exigent que tous les modèles soient ajustés sur
# le même échantillon. On réajuste M1, M2, M3 sur les obs
# complètes pour toutes les variables du modèle 3.

df_complet <- df %>%
  filter(!is.na(reoriente_bin),
         !is.na(conseil_adapte), !is.na(info_percue),
         !is.na(genre_bin), !is.na(niveau_parents_grp),
         !is.na(commune_grp), !is.na(filiere_grp),
         !is.na(psyen_bin),
         !is.na(ia_formation_bin), !is.na(ia_metiers_bin))

cat(sprintf("\nN (échantillon commun pour comparaisons) : %d\n", nrow(df_complet)))

m_null <- glm(reoriente_bin ~ 1, data = df_complet, family = binomial)
m1b    <- update(m1, data = df_complet)
m2b    <- update(m2, data = df_complet)
m3b    <- update(m3, data = df_complet)

cat("\n\n=============================================================\n")
cat("COMPARAISON DES MODÈLES (échantillon commun)\n")
cat("=============================================================\n")

aic_tab <- data.frame(
  Modele = c("M0 (null)", "M1 (advice)", "M2 (+ sociodemo)", "M3 (+ IA)"),
  N      = rep(nrow(df_complet), 4),
  AIC    = c(AIC(m_null), AIC(m1b), AIC(m2b), AIC(m3b)),
  BIC    = c(BIC(m_null), BIC(m1b), BIC(m2b), BIC(m3b)),
  Deviance = c(deviance(m_null), deviance(m1b), deviance(m2b), deviance(m3b))
)
print(round(aic_tab[, -1], 2))

cat("\nTests du rapport de vraisemblance (LR test) :\n")
cat("\nM0 vs M1 (apport de la qualité du conseil) :\n")
print(anova(m_null, m1b, test = "LRT"))
cat("\nM1 vs M2 (apport des variables sociodémographiques) :\n")
print(anova(m1b, m2b, test = "LRT"))
cat("\nM2 vs M3 (apport des variables IA) :\n")
print(anova(m2b, m3b, test = "LRT"))

# ------------------------------------------------------------
# 7. PSEUDO R² DE McFADDEN
# ------------------------------------------------------------
cat("\n\n=============================================================\n")
cat("PSEUDO R² DE McFADDEN (sur échantillon commun)\n")
cat("=============================================================\n")

mcfadden <- function(m, m_null) {
  as.numeric(1 - (logLik(m) / logLik(m_null)))
}

cat(sprintf("Pseudo R² M1 : %.3f\n", mcfadden(m1b, m_null)))
cat(sprintf("Pseudo R² M2 : %.3f\n", mcfadden(m2b, m_null)))
cat(sprintf("Pseudo R² M3 : %.3f\n", mcfadden(m3b, m_null)))

# ------------------------------------------------------------
# 8. SAUVEGARDE
# ------------------------------------------------------------
saveRDS(list(m1 = m1, m2 = m2, m3 = m3),
        "data/modeles_logistiques.rds")

cat("\n=============================================================\n")
cat("FIN DE LA RÉGRESSION LOGISTIQUE\n")
cat("=============================================================\n")
