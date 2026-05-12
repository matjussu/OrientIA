# ============================================================
# Script 00 : Pipeline complet
# Projet : OrientIA
# ============================================================
# Lance les 5 scripts dans l'ordre. Pratique pour relancer
# l'ensemble de l'analyse après une modification.
#
# USAGE :
#   - Depuis RStudio : ouvrir ce fichier et cliquer sur "Source"
#   - Depuis le terminal : Rscript 00_run_all.R
#
# Avant la première exécution, s'assurer que tous les packages
# requis sont installés (voir README.md).
# ============================================================

# Force une locale UTF-8 AVANT de sourcer les scripts. Sans cette étape,
# sur une machine dont le LANG système n'est pas UTF-8, source() avec
# encoding="UTF-8" peut casser les chaînes accentuées des commentaires
# et faire planter le parseur. On essaie d'abord la locale française,
# puis on retombe sur les alternatives universelles.
locales_a_tester <- c("fr_FR.UTF-8", "French_France.UTF-8",
                       "fr_FR.utf8", "C.UTF-8", "en_US.UTF-8")
loc_ok <- ""
for (loc in locales_a_tester) {
  res <- suppressWarnings(Sys.setlocale("LC_ALL", loc))
  if (res != "") { loc_ok <- loc; break }
}
if (loc_ok == "") {
  warning("Aucune locale UTF-8 disponible — les chaînes accentuées ",
          "risquent de mal s'afficher et certains tests peuvent diverger.")
}

cat("\n############################################################\n")
cat("# PIPELINE D'ANALYSE - PILOTE ORIENTIA\n")
cat("# Locale utilisée :", loc_ok, "\n")
cat("############################################################\n\n")

scripts <- c(
  "01_nettoyage_donnees.R",
  "02_stats_descriptives.R",
  "03_correlations.R",
  "04_regression_logistique.R",
  "05_visualisations.R"
)

t0 <- Sys.time()

for (s in scripts) {
  cat("\n>>> Exécution de :", s, "\n")
  cat(strrep("-", 60), "\n", sep = "")
  source(s, echo = FALSE, encoding = "UTF-8")
  cat(strrep("-", 60), "\n", sep = "")
  cat(">>> Terminé :", s, "\n")
}

t1 <- Sys.time()
cat("\n############################################################\n")
cat("# PIPELINE TERMINÉ en", round(as.numeric(t1 - t0, units = "secs"), 1), "secondes.\n")
cat("# Outputs :\n")
cat("#   - data/donnees_pilote_propres.csv  (dataset nettoyé)\n")
cat("#   - data/donnees_pilote_propres.rds  (idem, format R)\n")
cat("#   - data/modeles_logistiques.rds     (modèles M1/M2/M3)\n")
cat("#   - figures/01_motivation.png ... 08_parents_x_filiere.png\n")
cat("############################################################\n")
