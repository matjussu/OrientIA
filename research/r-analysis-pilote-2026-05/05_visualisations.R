# ============================================================
# Script 05 : Visualisations ggplot2
# Projet : OrientIA
# ============================================================

# Encoding UTF-8 (essai fr_FR puis fallback C.UTF-8 si indisponible).
suppressWarnings({
  res <- Sys.setlocale("LC_ALL", "fr_FR.UTF-8")
  if (res == "") Sys.setlocale("LC_ALL", "C.UTF-8")
})

library(dplyr)
library(ggplot2)
library(tidyr)
library(scales)

df <- readRDS("data/donnees_pilote_propres.rds")
dir.create("figures", showWarnings = FALSE)

palette_orient <- c("#2C3E50", "#E67E22", "#16A085", "#C0392B",
                    "#8E44AD", "#27AE60", "#D35400", "#7F8C8D")

theme_orient <- theme_minimal(base_size = 12) +
  theme(
    plot.title       = element_text(face = "bold", size = 13),
    plot.subtitle    = element_text(size = 10, color = "grey35"),
    plot.caption     = element_text(size = 9, color = "grey45"),
    panel.grid.minor = element_blank(),
    legend.position  = "bottom",
    plot.background  = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    legend.background = element_rect(fill = "white", color = NA),
    legend.key       = element_rect(fill = "white", color = NA)
  )

# ------------------------------------------------------------
# Figure 1 : Motivation initiale
# ------------------------------------------------------------
cat("Figure 1 : motivation initiale\n")

mot_data <- df %>%
  filter(!is.na(motivation_descriptive)) %>%
  count(motivation_descriptive) %>%
  mutate(
    pct = 100 * n / sum(n),
    nouvelle = motivation_descriptive %in% c("Professeurs du lycée",
                                              "Motivation personnelle / passion"),
    motivation_descriptive = factor(motivation_descriptive,
                                     levels = motivation_descriptive[order(n)])
  )

p1 <- ggplot(mot_data, aes(x = motivation_descriptive, y = pct, fill = nouvelle)) +
  geom_col() +
  geom_text(aes(label = sprintf("%.1f%% (n=%d)", pct, n)),
            hjust = -0.1, size = 3.5) +
  coord_flip() +
  scale_fill_manual(values = c("FALSE" = "#2C3E50", "TRUE" = "#E67E22"),
                    labels = c("Catégorie initiale", "Catégorie ajoutée au recodage"),
                    name = NULL) +
  scale_y_continuous(limits = c(0, max(mot_data$pct) * 1.20),
                     labels = function(x) paste0(x, "%")) +
  labs(
    title = "Sources de motivation pour le choix initial de formation",
    subtitle = sprintf("N = %d. Les professeurs du lycée pèsent davantage que le PsyEN.", sum(mot_data$n)),
    x = NULL, y = "% des répondants",
    caption = "Pilote OrientIA (2026)"
  ) +
  theme_orient

ggsave("figures/01_motivation.png", p1, width = 10, height = 6, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 2 : Likert horizontal stacked (palette diverging)
# ------------------------------------------------------------
cat("Figure 2 : variables Likert (stacked horizontal)\n")

likert_data <- df %>%
  select(info_percue, conseil_adapte, preparation_emploi) %>%
  pivot_longer(everything(), names_to = "variable", values_to = "valeur") %>%
  mutate(variable = dplyr::recode(variable,
    "info_percue"        = "Q13 - Information perçue",
    "conseil_adapte"     = "Q14 - Conseils adaptés",
    "preparation_emploi" = "Q15 - Préparation à l'emploi"
  )) %>%
  filter(!is.na(valeur)) %>%
  count(variable, valeur) %>%
  group_by(variable) %>%
  mutate(pct = 100 * n / sum(n)) %>%
  ungroup() %>%
  mutate(valeur = factor(valeur, levels = 1:5,
                         labels = c("1 (très mauvais)", "2", "3 (neutre)",
                                    "4", "5 (très bon)")))

# % négatif / neutre / positif par variable (pour annotations)
recap_likert <- df %>%
  select(info_percue, conseil_adapte, preparation_emploi) %>%
  pivot_longer(everything(), names_to = "variable", values_to = "valeur") %>%
  mutate(variable = dplyr::recode(variable,
    "info_percue"        = "Q13 - Information perçue",
    "conseil_adapte"     = "Q14 - Conseils adaptés",
    "preparation_emploi" = "Q15 - Préparation à l'emploi"
  )) %>%
  filter(!is.na(valeur)) %>%
  group_by(variable) %>%
  summarise(
    pct_neg = round(100 * mean(valeur <= 2)),
    pct_neu = round(100 * mean(valeur == 3)),
    pct_pos = round(100 * mean(valeur >= 4)),
    .groups = "drop"
  )

couleurs_likert <- c(
  "1 (très mauvais)" = "#C0392B",
  "2"                = "#E67E22",
  "3 (neutre)"       = "#BDC3C7",
  "4"                = "#52B788",
  "5 (très bon)"     = "#1B7F4F"
)

p2 <- ggplot(likert_data, aes(x = variable, y = pct, fill = valeur)) +
  geom_col(position = position_stack(reverse = TRUE), width = 0.7) +
  geom_text(aes(label = ifelse(pct >= 6, sprintf("%.0f%%", pct), "")),
            position = position_stack(vjust = 0.5, reverse = TRUE),
            size = 3.2, color = "white", fontface = "bold") +
  geom_text(data = recap_likert,
            aes(x = variable, y = -3,
                label = sprintf("%d%%\nnégatif", pct_neg)),
            inherit.aes = FALSE,
            size = 3.1, color = "#C0392B", hjust = 1) +
  geom_text(data = recap_likert,
            aes(x = variable, y = 103,
                label = sprintf("%d%%\npositif", pct_pos)),
            inherit.aes = FALSE,
            size = 3.1, color = "#1B7F4F", hjust = 0) +
  coord_flip() +
  scale_fill_manual(values = couleurs_likert, name = NULL) +
  scale_y_continuous(limits = c(-15, 115),
                     breaks = seq(0, 100, 25),
                     labels = function(x) paste0(x, "%")) +
  labs(
    title = "Perceptions sur l'orientation et l'information",
    subtitle = "Distribution des réponses sur l'échelle 1-5 (1 = très mauvais, 5 = très bon)",
    x = NULL, y = "% des répondants",
    caption = "Pilote OrientIA (2026)"
  ) +
  theme_orient +
  theme(legend.position = "bottom")

ggsave("figures/02_likert.png", p2, width = 11, height = 5.5, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 3 : Conseil adapté selon le niveau d'études des parents
# ------------------------------------------------------------
# IMPORTANT : la figure montre les 5 catégories interprétables. Le p-value
# du sous-titre est recalculé en direct sur CES 5 catégories pour rester
# cohérent avec ce qui est affiché (et avec ce que dit le rapport :
# H = 6,38 ; p = 0,173, sur N = 176). Avant correction, le sous-titre
# affichait p = 0,038 (la valeur du test sur 7 catégories, qui inclut
# "Autre" n=3 et "Préfère ne pas répondre" n=1 — non interprétables).
cat("Figure 3 : conseil adapté ~ niveau parents (refaite en pointrange)\n")

niv_parents_ordre <- c("Aucun diplôme / Brevet", "CAP / BEP", "Baccalauréat",
                       "Bac+2 / Bac+3", "Bac+5 et plus")

p3_data <- df %>%
  filter(niveau_parents %in% niv_parents_ordre) %>%
  mutate(niveau_parents = factor(niveau_parents, levels = niv_parents_ordre))

# Calcul des moyennes et IC 95% (méthode t-test classique sur Likert)
p3_summary <- p3_data %>%
  group_by(niveau_parents) %>%
  summarise(
    n   = n(),
    moy = mean(conseil_adapte, na.rm = TRUE),
    sd  = sd(conseil_adapte, na.rm = TRUE),
    se  = sd / sqrt(n),
    ic_bas  = moy - qt(0.975, df = n - 1) * se,
    ic_haut = moy + qt(0.975, df = n - 1) * se,
    .groups = "drop"
  )

# Moyenne globale (pour la ligne de référence)
moy_globale_q14 <- mean(p3_data$conseil_adapte, na.rm = TRUE)

# Test de Kruskal-Wallis sur les 5 catégories effectivement affichées.
# On formate le p en virgule décimale pour cohérence francophone.
kw_p3 <- kruskal.test(conseil_adapte ~ niveau_parents, data = p3_data)
p_value_str <- sub("\\.", ",", sprintf("%.3f", kw_p3$p.value))

p3 <- ggplot(p3_summary, aes(x = niveau_parents, y = moy)) +
  geom_hline(yintercept = moy_globale_q14, linetype = "dashed",
             color = "grey50", linewidth = 0.5) +
  geom_pointrange(aes(ymin = ic_bas, ymax = ic_haut),
                  color = "#16A085", size = 0.8, linewidth = 0.9) +
  geom_text(aes(label = sprintf("μ=%.2f\nn=%d", moy, n),
                y = ic_haut + 0.15),
            size = 3.1, color = "grey25", vjust = 0) +
  scale_y_continuous(breaks = 1:5, limits = c(1.5, 4.7)) +
  labs(
    title = "Qualité du conseil reçu selon le niveau d'études des parents",
    subtitle = sprintf("Moyennes avec IC 95%%. Moyenne globale = %.2f (ligne pointillée). Kruskal-Wallis (5 catégories, N = %d) : p = %s.",
                       moy_globale_q14, nrow(p3_data), p_value_str),
    x = "Niveau d'études le plus élevé des parents",
    y = "Conseil adapté au profil (Q14, moyenne sur échelle 1-5)",
    caption = "Pilote OrientIA (2026). IC larges pour les groupes à faible effectif (notamment Aucun diplôme et Bac)."
  ) +
  theme_orient +
  theme(axis.text.x = element_text(angle = 20, hjust = 1))

ggsave("figures/03_conseil_x_parents.png", p3, width = 10, height = 6, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 4 : Taux de réorientation par filière
# ------------------------------------------------------------
cat("Figure 4 : réorientation par filière\n")

p4_data <- df %>%
  filter(!is.na(filiere), !is.na(reoriente_bin)) %>%
  group_by(filiere) %>%
  summarise(n_total   = n(),
            n_reor    = sum(reoriente_bin),
            taux_reor = 100 * mean(reoriente_bin),
            .groups   = "drop") %>%
  filter(n_total >= 4) %>%
  mutate(filiere = factor(filiere, levels = filiere[order(taux_reor)]))

moy_globale <- mean(df$reoriente_bin, na.rm = TRUE) * 100

p4 <- ggplot(p4_data, aes(x = filiere, y = taux_reor)) +
  geom_col(fill = "#E67E22") +
  geom_hline(yintercept = moy_globale, linetype = "dashed", color = "#C0392B") +
  geom_text(aes(label = sprintf("%.0f%% (%d/%d)", taux_reor, n_reor, n_total)),
            hjust = -0.1, size = 3.2) +
  coord_flip() +
  scale_y_continuous(limits = c(0, 95), labels = function(x) paste0(x, "%")) +
  annotate("text", x = 1.5, y = moy_globale + 2, hjust = 0,
           label = sprintf("Moyenne échantillon : %.0f%%", moy_globale),
           color = "#C0392B", size = 3.2) +
  labs(
    title = "Taux de réorientation par filière",
    subtitle = "Chi-2 : p = 0,006. Lettres/SHS et écoles d'art au-dessus de la moyenne.",
    x = NULL, y = "% de répondants ayant changé de filière",
    caption = "Pilote OrientIA (2026). Filières avec n < 4 exclues."
  ) +
  theme_orient

ggsave("figures/04_reorientation_par_filiere.png", p4, width = 11, height = 6, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 5 : Niveau de réorientation
# ------------------------------------------------------------
cat("Figure 5 : niveau de réorientation\n")

p5_data <- df %>%
  filter(reoriente_bin == 1, !is.na(reorientation_niveau)) %>%
  count(reorientation_niveau) %>%
  mutate(reorientation_niveau = factor(reorientation_niveau,
                                       levels = c("L1", "L2", "L3", "M1", "M2", "Post-L3")))

p5 <- ggplot(p5_data, aes(x = reorientation_niveau, y = n)) +
  geom_col(fill = "#2C3E50") +
  geom_text(aes(label = n), vjust = -0.5, size = 4) +
  labs(
    title = "À quel niveau d'études les étudiants se réorientent-ils ?",
    subtitle = "Niveau au moment du changement (info exploitée pour 37 des 53 réorientés)",
    x = "Niveau d'études", y = "Nombre de réorientations",
    caption = "Pilote OrientIA (2026). Cas ambigus exclus."
  ) +
  scale_y_continuous(limits = c(0, max(p5_data$n) * 1.15)) +
  theme_orient

ggsave("figures/05_niveau_reorientation.png", p5, width = 9, height = 5, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 6 : Usage de l'IA selon le contexte (anciennement fig 7)
# ------------------------------------------------------------
cat("Figure 6 : usage de l'IA\n")

ia_long <- df %>%
  select(ia_formation, ia_metiers) %>%
  pivot_longer(everything(), names_to = "contexte", values_to = "usage") %>%
  mutate(contexte = dplyr::recode(contexte,
                           "ia_formation" = "Choix de formation",
                           "ia_metiers"   = "Exploration des métiers")) %>%
  filter(!is.na(usage)) %>%
  count(contexte, usage) %>%
  group_by(contexte) %>%
  mutate(pct = 100 * n / sum(n)) %>%
  ungroup() %>%
  mutate(usage = factor(usage,
                        levels = c("Non",
                                   "Oui, en complément d'autres démarches",
                                   "Oui, de manière exclusive")))

p7 <- ggplot(ia_long, aes(x = contexte, y = pct, fill = usage)) +
  geom_col(position = "stack") +
  geom_text(aes(label = ifelse(pct >= 5, sprintf("%.1f%%", pct), "")),
            position = position_stack(vjust = 0.5), size = 3.5, color = "white") +
  scale_fill_manual(values = c("Non" = "#7F8C8D",
                               "Oui, en complément d'autres démarches" = "#2C3E50",
                               "Oui, de manière exclusive" = "#E67E22"),
                    name = NULL) +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title = "Usage de l'IA générale dans le parcours d'orientation",
    subtitle = "L'IA est plus mobilisée pour explorer les métiers que pour choisir une formation.",
    x = NULL, y = "% des répondants",
    caption = "Pilote OrientIA (2026)"
  ) +
  theme_orient

ggsave("figures/06_usage_ia.png", p7, width = 10, height = 6, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 7 : Q16.3 distribution bimodale (anciennement fig 8)
# ------------------------------------------------------------
cat("Figure 7 : regret\n")

p8_data <- df %>%
  filter(reoriente_bin == 1, !is.na(regret_reorientation)) %>%
  count(regret_reorientation) %>%
  mutate(pct = 100 * n / sum(n))

p8 <- ggplot(p8_data, aes(x = factor(regret_reorientation), y = pct)) +
  geom_col(fill = "#8E44AD") +
  geom_text(aes(label = sprintf("%.1f%%\n(n=%d)", pct, n)),
            vjust = -0.3, size = 3.4) +
  scale_y_continuous(limits = c(0, max(p8_data$pct) * 1.20),
                     labels = function(x) paste0(x, "%")) +
  labs(
    title = "Q16.3 - De meilleurs conseils auraient-ils évité la réorientation ?",
    subtitle = sprintf("Parmi les %d réorientés. Distribution polarisée.", sum(p8_data$n)),
    x = "Échelle 1 (pas du tout) à 5 (tout à fait)",
    y = "% des réorientés",
    caption = "Pilote OrientIA (2026)"
  ) +
  theme_orient

ggsave("figures/07_regret_reorientation.png", p8, width = 9, height = 5, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Figure 8 : Niveau parents x Filière (reproduction sociale)
# ------------------------------------------------------------
# Test : Chi-2 = 10,47 ; df = 4 ; p = 0,033 (significatif).
# Fisher exact (Monte-Carlo) : p = 0,036.
cat("Figure 8 : niveau parents x filière\n")

# Préparation des variables groupées
p9_data <- df %>%
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
                     "Santé (médecine, pharmacie, kiné, infirmier…)") ~ "École sélective",
      filiere %in% c("Économie / Gestion / Commerce",
                     "Droit / Science politique") ~ "Université éco / droit",
      filiere %in% c("Lettres / Sciences humaines / Sciences sociales",
                     "Sciences / Mathématiques / Informatique") ~ "Université généraliste",
      TRUE ~ NA_character_
    )
  ) %>%
  filter(!is.na(niveau_parents_grp), !is.na(filiere_grp)) %>%
  count(niveau_parents_grp, filiere_grp) %>%
  group_by(niveau_parents_grp) %>%
  mutate(pct = 100 * n / sum(n),
         total = sum(n)) %>%
  ungroup() %>%
  mutate(
    niveau_parents_grp = factor(niveau_parents_grp,
                                 levels = c("Faible", "Intermédiaire", "Supérieur")),
    filiere_grp = factor(filiere_grp,
                         levels = c("Université généraliste",
                                    "Université éco / droit",
                                    "École sélective"))
  )

# Annotation effectifs totaux par groupe
totaux_p9 <- p9_data %>% distinct(niveau_parents_grp, total)

p9 <- ggplot(p9_data, aes(x = niveau_parents_grp, y = pct, fill = filiere_grp)) +
  geom_col(position = "stack") +
  geom_text(aes(label = ifelse(pct >= 8, sprintf("%.0f%%\n(n=%d)", pct, n), "")),
            position = position_stack(vjust = 0.5),
            size = 3.4, color = "white", fontface = "bold") +
  geom_text(data = totaux_p9,
            aes(x = niveau_parents_grp, y = 103,
                label = sprintf("Total\nn = %d", total)),
            inherit.aes = FALSE, size = 3.2, color = "grey25") +
  scale_fill_manual(values = c("Université généraliste" = "#E67E22",
                                "Université éco / droit" = "#2C3E50",
                                "École sélective"       = "#16A085"),
                    name = NULL) +
  scale_y_continuous(limits = c(0, 110),
                     breaks = seq(0, 100, 25),
                     labels = function(x) paste0(x, "%")) +
  labs(
    title = "Filière choisie selon le niveau d'études des parents",
    subtitle = "Chi-2 : p = 0,033. Les enfants de parents peu diplômés se dirigent davantage vers les filières universitaires généralistes.",
    x = "Niveau d'études le plus élevé des parents",
    y = "% des étudiants",
    caption = "Pilote OrientIA (2026). Combiné avec la fig. 4 (Lettres/SHS = 62% de réorientations), suggère un effet en chaîne."
  ) +
  theme_orient

ggsave("figures/08_parents_x_filiere.png", p9, width = 11, height = 6, dpi = 200, bg = "white")

cat("\nToutes les figures sont sauvegardées dans le dossier ./figures/\n")
print(list.files("figures", full.names = TRUE))
