# ============================================================
# Script 02 : Statistiques descriptives
# Projet : OrientIA
# ============================================================

# Encoding UTF-8 pour l'affichage et la comparaison des caractères français.
# On essaie d'abord fr_FR.UTF-8, et si la locale n'est pas installée
# sur la machine on retombe sur C.UTF-8 (toujours disponible sous Linux).
# Sans ce fallback, sur une machine qui n'a pas fr_FR.UTF-8, les case_when
# avec chaînes accentuées échouent silencieusement et tous les croisements
# sortent faux.
suppressWarnings({
  res <- Sys.setlocale("LC_ALL", "fr_FR.UTF-8")
  if (res == "") Sys.setlocale("LC_ALL", "C.UTF-8")
})

library(dplyr)
library(readr)
library(tidyr)
library(stringr)

df <- readRDS("data/donnees_pilote_propres.rds")

# Petit utilitaire pour afficher proprement les distributions catégorielles
distribution <- function(x, nom = NULL) {
  if (!is.null(nom)) cat("\n--- ", nom, " ---\n", sep = "")
  tab <- table(x, useNA = "ifany")
  pct <- round(100 * prop.table(tab), 1)
  res <- data.frame(modalite = names(tab), n = as.integer(tab), pct = as.numeric(pct))
  res <- res[order(-res$n), ]
  print(res, row.names = FALSE)
}

cat("=============================================================\n")
cat("STATISTIQUES DESCRIPTIVES - PILOTE ORIENTIA\n")
cat("=============================================================\n")
cat("N total :", nrow(df), "\n")
cat("Dont étudiants actuels :", sum(df$statut_etudiant == "Oui", na.rm = TRUE), "\n")
cat("Dont jeunes actifs :", sum(df$jeune_actif, na.rm = TRUE), "\n")

# ------------------------------------------------------------
# 1. PROFIL SOCIODÉMOGRAPHIQUE
# ------------------------------------------------------------
cat("\n\n############# 1. PROFIL SOCIODÉMOGRAPHIQUE #############\n")
distribution(df$genre, "Genre")
distribution(df$type_commune, "Type de commune (lycée)")
distribution(df$niveau_parents, "Niveau d'études des parents")
distribution(df$type_bac, "Type de bac")
distribution(df$mention_bac, "Mention au bac")
distribution(df$annee_etudes, "Année d'études actuelle")
distribution(df$filiere, "Filière")

# ------------------------------------------------------------
# 2. EXPÉRIENCE D'ORIENTATION
# ------------------------------------------------------------
cat("\n\n############# 2. EXPÉRIENCE D'ORIENTATION #############\n")
distribution(df$frequence_psyen, "Fréquence rencontre PsyEN")
distribution(df$motivation_descriptive, "Motivation initiale (codage descriptif)")

# ------------------------------------------------------------
# 3. USAGE DE L'IA
# ------------------------------------------------------------
cat("\n\n############# 3. USAGE DE L'IA #############\n")
distribution(df$ia_formation, "IA pour le choix de formation")
distribution(df$ia_metiers, "IA pour l'exploration des métiers")

# ------------------------------------------------------------
# 4. VARIABLES SUR ÉCHELLE DE LIKERT (1 à 5)
# ------------------------------------------------------------
cat("\n\n############# 4. PERCEPTIONS (échelles 1-5) #############\n")

likert_summary <- function(x, nom) {
  cat("\n--- ", nom, " ---\n", sep = "")
  cat(sprintf("  N        : %d (NA: %d)\n", sum(!is.na(x)), sum(is.na(x))))
  cat(sprintf("  Moyenne  : %.2f\n", mean(x, na.rm = TRUE)))
  cat(sprintf("  Médiane  : %.1f\n", median(x, na.rm = TRUE)))
  cat(sprintf("  Écart-type : %.2f\n", sd(x, na.rm = TRUE)))
  cat("  Distribution :\n")
  for (i in 1:5) {
    n <- sum(x == i, na.rm = TRUE)
    pct <- round(100 * n / sum(!is.na(x)), 1)
    cat(sprintf("    %d : %3d (%s%%)\n", i, n, pct))
  }
}

likert_summary(df$info_percue, "Q13 - Information perçue avant le choix")
likert_summary(df$conseil_adapte, "Q14 - Conseils adaptés au profil")
likert_summary(df$preparation_emploi, "Q15 - Préparation au marché du travail (exploratoire)")

# ------------------------------------------------------------
# 5. RÉORIENTATION
# ------------------------------------------------------------
cat("\n\n############# 5. RÉORIENTATION #############\n")
distribution(df$reoriente, "Statut de réorientation")
cat(sprintf("\nTaux de réorientation : %.1f%% (%d / %d)\n",
            100 * mean(df$reoriente_bin, na.rm = TRUE),
            sum(df$reoriente_bin, na.rm = TRUE),
            sum(!is.na(df$reoriente_bin))))

# Sous-population réorientés uniquement
df_reor <- df %>% filter(reoriente_bin == 1)
cat("\n--- Parmi les réorientés (N =", nrow(df_reor), ") ---\n")
distribution(df_reor$reorientation_niveau, "Niveau d'études lors de la réorientation")
distribution(df_reor$reorientation_annee, "Année calendaire de réorientation")
distribution(df_reor$raison_reorientation, "Raison principale")
likert_summary(df_reor$regret_reorientation,
               "Q16.3 - Conseils auraient évité la réorientation")

cat("\n=============================================================\n")
cat("FIN DES STATISTIQUES DESCRIPTIVES\n")
cat("=============================================================\n")
