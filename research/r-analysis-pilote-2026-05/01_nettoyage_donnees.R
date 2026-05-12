# ============================================================
# Script 01 : Import et nettoyage des données du pilote
# Projet : OrientIA
# Date : mai 2026
# ============================================================
# Ce script :
#   1. Importe les réponses brutes du Google Forms
#   2. Renomme les colonnes en variables courtes et explicites
#   3. Recode les réponses libres ("Autre") en catégories exploitables
#   4. Crée un double codage pour la variable motivation
#   5. Sépare le champ libre "année de réorientation" en deux variables
#   6. Exporte un dataset propre prêt pour les analyses
# ============================================================

# Encoding UTF-8 pour l'affichage des caractères français
suppressWarnings({
  Sys.setlocale("LC_CTYPE", "fr_FR.UTF-8")
  Sys.setlocale("LC_ALL", "fr_FR.UTF-8")
})

library(tidyverse)

# Forcer la locale en UTF-8 pour gérer correctement les accents.
# Sur Windows, remplacer par : Sys.setlocale("LC_ALL", "French_France.UTF-8")
Sys.setlocale("LC_ALL", "C.UTF-8")

# ------------------------------------------------------------
# 1. IMPORT
# ------------------------------------------------------------
# Le script cherche le fichier CSV brut dans le dossier data/.
# Pour adapter à un autre nom de fichier, modifier ci-dessous.

fichier_entree <- "data/donnees_brutes.csv"

if (!file.exists(fichier_entree)) {
  # Cherche automatiquement le premier CSV présent dans data/
  csvs <- list.files("data", pattern = "\\.csv$", full.names = TRUE,
                     ignore.case = TRUE)
  csvs <- csvs[!grepl("donnees_pilote_propres", csvs)]  # exclut les sorties
  if (length(csvs) == 0) {
    stop("Aucun fichier CSV trouvé dans data/. ",
         "Place le fichier exporté de Google Forms dans ce dossier.")
  }
  fichier_entree <- csvs[1]
  message("Fichier détecté automatiquement : ", fichier_entree)
}

df_raw <- read_csv(
  fichier_entree,
  show_col_types = FALSE,
  locale = locale(encoding = "UTF-8")
)

cat("Nombre de réponses brutes :", nrow(df_raw), "\n")

# ------------------------------------------------------------
# 2. RENOMMAGE DES COLONNES
# ------------------------------------------------------------

df <- df_raw %>%
  rename(
    horodateur            = 1,
    statut_etudiant       = 2,   # Q1
    annee_etudes          = 3,   # Q2
    genre                 = 4,   # Q3
    type_commune          = 5,   # Q4
    niveau_parents        = 6,   # Q5
    type_bac              = 7,   # Q6
    mention_bac           = 8,   # Q7
    filiere               = 9,   # Q8
    frequence_psyen       = 10,  # Q9
    motivation_brut       = 11,  # Q10
    ia_formation          = 12,  # Q11
    ia_metiers            = 13,  # Q12
    info_percue           = 14,  # Q13 (contenu + débouchés, déjà fusionné)
    conseil_adapte        = 15,  # Q14
    preparation_emploi    = 16,  # Q15 (exploratoire uniquement)
    reoriente             = 17,  # Q16
    reorientation_brut    = 18,  # Q16.1
    raison_reorientation  = 19,  # Q16.2
    regret_reorientation  = 20   # Q16.3
  )

# ------------------------------------------------------------
# 3. CAS PARTICULIERS DÉTECTÉS DANS LES DONNÉES BRUTES
# ------------------------------------------------------------

# 3.1 Réponse "surveyswap" : la personne a coché "Famille / entourage / réseau"
# puis ajouté un message en aparté (conseil sur un site de diffusion).
# On nettoie le champ pour ne garder que la réponse réelle.
df <- df %>%
  mutate(motivation_brut = if_else(
    str_detect(motivation_brut, regex("surveyswap", ignore_case = TRUE)),
    "Famille / entourage / réseau",
    motivation_brut
  ))

# 3.2 Réponse "Hauts-de-Seine" : commentaire hors-sujet à la question Q10.
# On bascule en NA pour ne pas polluer l'analyse de la motivation.
df <- df %>%
  mutate(motivation_brut = if_else(
    str_detect(motivation_brut, regex("haut.{0,3}seine", ignore_case = TRUE)),
    NA_character_,
    motivation_brut
  ))

# ------------------------------------------------------------
# 4. RECODAGE DE LA FILIÈRE (Q8)
# ------------------------------------------------------------
# Les réponses libres "BTS" et "IUT / BUT" désignent des types
# d'établissement plutôt que des filières disciplinaires : passées en NA.

df <- df %>%
  mutate(filiere = case_when(
    # Économie / Gestion / Commerce
    filiere %in% c(
      "Pas actuellement inscrit. Anciennement inscrit en Economie",
      "Economie du développement",
      "Gestion de patrimoine",
      "Développement agroéconomique"
    ) ~ "Économie / Gestion / Commerce",

    # Lettres / Sciences humaines / Sciences sociales
    filiere %in% c(
      "Master MEEF",
      "Enseignement (meef doc)",
      "Médiation culturelle",
      "Communication",
      "Histoire",
      "Urbanisme"
    ) ~ "Lettres / Sciences humaines / Sciences sociales",

    # Sciences / Mathématiques / Informatique
    filiere == "sciences de la vie" ~ "Sciences / Mathématiques / Informatique",

    # École d'art / design / architecture
    filiere == "Diplôme pro en Infographie" ~ "École d'art / design / architecture",

    # Cas double diplôme : filière initiale = droit
    str_detect(filiere, regex("droit des affaires", ignore_case = TRUE)) ~
      "Droit / Science politique",

    # Trop ambigus pour être recodés
    filiere %in% c("BTS", "IUT / BUT") ~ NA_character_,

    # Toutes les autres réponses (catégories standard) restent inchangées
    TRUE ~ filiere
  ))

# ------------------------------------------------------------
# 5. DOUBLE CODAGE DE LA MOTIVATION (Q10)
# ------------------------------------------------------------
# Deux versions sont créées :
#   - motivation_descriptive : catégories enrichies pour les stats descriptives
#     (fait apparaître les profs et la motivation personnelle, sous-représentés
#      dans les options initiales du formulaire)
#   - motivation_regression : catégories agrégées pour la régression logistique
#     (évite les modalités à très faible effectif qui rendent les estimations
#      instables)

categories_standard <- c(
  "Famille / entourage / réseau",
  "Journées portes ouvertes / salons",
  "Internet (hors IA) — forums, sites officiels",
  "Aucune source structurée / au hasard",
  "Conseiller d'orientation (PsyEN)",
  "Intelligence artificielle (ChatGPT, Gemini…)"
)

# 5.1 Version descriptive (catégories enrichies)
df <- df %>%
  mutate(motivation_descriptive = case_when(

    # NA conservés
    is.na(motivation_brut) ~ NA_character_,

    # Catégories standard du formulaire
    motivation_brut %in% categories_standard ~ motivation_brut,

    # Nouvelle catégorie : Professeurs du lycée
    # (couvre "Profs", "Professeur", "Professeurs du lycée",
    #  "Mes professeurs, mes spécialisations...", etc.)
    str_detect(str_to_lower(motivation_brut), "prof") ~ "Professeurs du lycée",

    # Nouvelle catégorie : Motivation personnelle / passion
    str_detect(
      str_to_lower(motivation_brut),
      "passion|aime|goût|projet|motivation personnelle|bon dans|spécialisation"
    ) ~ "Motivation personnelle / passion",

    # Cas particulier : "Pas accepté ailleurs" = choix subi
    # str_detect plutôt que == pour gérer les espaces en fin de chaîne
    str_detect(motivation_brut, regex("^Pas accepté ailleurs", ignore_case = TRUE)) ~
      "Aucune source structurée / au hasard",

    # Note : le cas "famille entourage et professeurs du lycée" est classé
    # dans "Professeurs du lycée" via la règle prof ci-dessus, ce qui renforce
    # une catégorie sous-représentée dans les options du formulaire.

    # Tout le reste : Autre
    TRUE ~ "Autre"
  ))

# 5.2 Version pour régression (modalités agrégées)
df <- df %>%
  mutate(motivation_regression = case_when(
    motivation_descriptive %in% c(
      "Professeurs du lycée",
      "Motivation personnelle / passion"
    ) ~ "Autre",
    TRUE ~ motivation_descriptive
  ))

# ------------------------------------------------------------
# 6. SPLIT DE L'ANNÉE DE RÉORIENTATION (Q16.1)
# ------------------------------------------------------------
# Le champ libre mélange années calendaires (2021, 2023...) et niveaux
# d'études (L1, M1, "3ème année", "première année"...).
# On extrait les deux informations dans deux variables distinctes.

# 6.1 Extraction de l'année calendaire (ex : 2018-2026)
extraire_annee <- function(x) {
  if (is.na(x)) return(NA_integer_)
  m <- str_extract(x, "\\b(201[8-9]|202[0-6])\\b")
  if (is.na(m)) return(NA_integer_)
  as.integer(m)
}

# 6.2 Extraction du niveau d'études
# Convention : "3" / "3ème" / "3e année" = L3 (3e année post-bac)
#              "4" / "4eme" = M1 (4e année post-bac)
#              "5" / "5e"   = M2 (5e année post-bac)
extraire_niveau <- function(x) {
  if (is.na(x)) return(NA_character_)
  xl <- str_trim(str_to_lower(x))

  # Format direct L1/L2/L3/M1/M2
  m <- str_extract(xl, "\\b[lm][1-3]\\b")
  if (!is.na(m)) return(toupper(m))

  # Niveau L1
  if (str_detect(xl, "première année|1ère année|premiere annee|licence 1|^1$")) {
    return("L1")
  }
  # Niveau L2
  if (str_detect(xl, "deuxième année|2ème année|2eme année|licence 2|fin de la l2|2eme a 3|^2$")) {
    return("L2")
  }
  # Niveau L3
  if (str_detect(xl, "troisième année|3ème année|3eme année|licence 3|3 ème|^3ème$|^3eme$|^3$|à 3 ème")) {
    return("L3")
  }
  # Niveau M1
  if (str_detect(xl, "master 1|première année de master|premiere annee de master|^4eme$|^4ème$|^4$")) {
    return("M1")
  }
  # Niveau M2
  if (str_detect(xl, "master 2|deuxième année de master|^5e$|^5ème$|^5$")) {
    return("M2")
  }
  # Réorientation après la licence (vers un master différent)
  if (str_detect(xl, "après la licence|après un diplôme|pour le master|après la l3|fin 2024")) {
    return("Post-L3")
  }

  return(NA_character_)
}

df <- df %>%
  mutate(
    reorientation_annee  = map_int(reorientation_brut, extraire_annee),
    reorientation_niveau = map_chr(reorientation_brut, extraire_niveau)
  )

# Cohérence : si reoriente == "Non...", on force NA sur les deux variables
# (cas des réponses "Pas le cas" / "Non" dans le champ libre)
df <- df %>%
  mutate(
    reorientation_annee = if_else(
      str_detect(reoriente, regex("^Non", ignore_case = TRUE)),
      NA_integer_,
      reorientation_annee
    ),
    reorientation_niveau = if_else(
      str_detect(reoriente, regex("^Non", ignore_case = TRUE)),
      NA_character_,
      reorientation_niveau
    )
  )

# ------------------------------------------------------------
# 7. VARIABLES DÉRIVÉES
# ------------------------------------------------------------

df <- df %>%
  mutate(

    # Variable binaire de réorientation (pour la régression logistique)
    reoriente_bin = case_when(
      str_detect(reoriente, regex("^Oui", ignore_case = TRUE)) ~ 1L,
      str_detect(reoriente, regex("^Non", ignore_case = TRUE)) ~ 0L,
      TRUE ~ NA_integer_
    ),

    # Variable binaire d'usage de l'IA pour la formation
    ia_formation_bin = case_when(
      str_detect(ia_formation, regex("^Oui", ignore_case = TRUE)) ~ 1L,
      ia_formation == "Non" ~ 0L,
      TRUE ~ NA_integer_
    ),

    # Variable binaire d'usage de l'IA pour les métiers
    ia_metiers_bin = case_when(
      str_detect(ia_metiers, regex("^Oui", ignore_case = TRUE)) ~ 1L,
      ia_metiers == "Non" ~ 0L,
      TRUE ~ NA_integer_
    ),

    # Flag jeune actif (pour stat descriptive seulement, non utilisé en régression)
    jeune_actif = if_else(statut_etudiant == "Non", 1L, 0L)
  )

# ------------------------------------------------------------
# 8. CONTRÔLE QUALITÉ
# ------------------------------------------------------------

cat("\n=== Contrôle après nettoyage ===\n")
cat("N total :", nrow(df), "\n")
cat("Dont jeunes actifs :", sum(df$jeune_actif, na.rm = TRUE), "\n")
cat("Dont réorientés :", sum(df$reoriente_bin, na.rm = TRUE), "\n")

cat("\n--- Filière (après recodage) ---\n")
print(table(df$filiere, useNA = "ifany"))

cat("\n--- Motivation (descriptive) ---\n")
print(table(df$motivation_descriptive, useNA = "ifany"))

cat("\n--- Motivation (régression) ---\n")
print(table(df$motivation_regression, useNA = "ifany"))

cat("\n--- Niveau de réorientation ---\n")
print(table(df$reorientation_niveau, useNA = "ifany"))

cat("\n--- Année calendaire de réorientation ---\n")
print(table(df$reorientation_annee, useNA = "ifany"))

# ------------------------------------------------------------
# 9. EXPORT
# ------------------------------------------------------------

write_csv(df, "data/donnees_pilote_propres.csv")
saveRDS(df, "data/donnees_pilote_propres.rds")

cat("\nDataset exporté : data/donnees_pilote_propres.csv et .rds\n")
