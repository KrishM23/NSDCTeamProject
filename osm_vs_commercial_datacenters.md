Comparing OpenStreetMap facility counts against the commercial tracker
numbers across countries
================
CHARISSA MAK
2026-10-30

``` r
#country-level summary and individual facility data
country_summary <- read_csv("clean_country_summary.csv")
data_centers <- read_csv("clean_data_centers.csv")

#preview of country summary structure
glimpse(country_summary)
```

    ## Rows: 116
    ## Columns: 7
    ## $ country                   <chr> "United States of America", "France", "Germa…
    ## $ continent                 <chr> "North America", "Europe", "Europe", "Europe…
    ## $ subregion                 <chr> "Northern America", "Western Europe", "Weste…
    ## $ osm_facilities            <dbl> 1789, 371, 300, 293, 167, 139, 127, 125, 88,…
    ## $ total_footprint_m2        <dbl> 37935947, 1591964, 1341617, 1819135, 2405700…
    ## $ median_footprint_m2       <dbl> 11341, 2061, 2250, 3855, 5380, 4451, 2484, 6…
    ## $ kind_research_or_academic <dbl> 13, 10, 7, 3, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, …

some descriptive statistics

``` r
#summary statistics for facility counts and footprints across countries
summary_table <- country_summary %>%
  summarise(
    Total_Countries = n(),
    Total_OSM_Facilities = sum(osm_facilities, na.rm = TRUE),
    Mean_Facilities_Per_Country = mean(osm_facilities, na.rm = TRUE),
    Median_Facilities_Per_Country = median(osm_facilities, na.rm = TRUE),
    Max_Facilities = max(osm_facilities, na.rm = TRUE),
    Mean_Total_Footprint_m2 = mean(total_footprint_m2, na.rm = TRUE),
    Median_Total_Footprint_m2 = median(total_footprint_m2, na.rm = TRUE)
  )

knitr::kable(summary_table, caption = "Global Overview of Mapped Data Center Metrics")
```

| Total_Countries | Total_OSM_Facilities | Mean_Facilities_Per_Country | Median_Facilities_Per_Country | Max_Facilities | Mean_Total_Footprint_m2 | Median_Total_Footprint_m2 |
|---:|---:|---:|---:|---:|---:|---:|
| 116 | 4800 | 41.37931 | 5.5 | 1789 | 684027.4 | 30196 |

Global Overview of Mapped Data Center Metrics

which countries dominate the crowdsourced mapping registry

``` r
top_countries <- country_summary %>%
  arrange(desc(osm_facilities)) %>%
  head(10)

knitr::kable(top_countries, caption = "Top 10 Countries by OpenStreetMap Facility Count")
```

| country | continent | subregion | osm_facilities | total_footprint_m2 | median_footprint_m2 | kind_research_or_academic |
|:---|:---|:---|---:|---:|---:|---:|
| United States of America | North America | Northern America | 1789 | 37935947 | 11341 | 13 |
| France | Europe | Western Europe | 371 | 1591964 | 2061 | 10 |
| Germany | Europe | Western Europe | 300 | 1341617 | 2250 | 7 |
| United Kingdom | Europe | Northern Europe | 293 | 1819135 | 3855 | 3 |
| Netherlands | Europe | Western Europe | 167 | 2405700 | 5380 | 0 |
| Australia | Oceania | Australia and New Zealand | 139 | 800667 | 4451 | 0 |
| Japan | Asia | Eastern Asia | 127 | 270889 | 2484 | 0 |
| China | Asia | Eastern Asia | 125 | 2709871 | 6613 | 0 |
| Canada | North America | Northern America | 88 | 631520 | 6447 | 0 |
| Ireland | Europe | Northern Europe | 86 | 944262 | 8987 | 0 |

Top 10 Countries by OpenStreetMap Facility Count

``` r
#top 12 countries. also convert footprint to square kilometers for readability
plot_data <- country_summary %>%
  arrange(desc(osm_facilities)) %>%
  head(12) %>%
  mutate(
            country = fct_reorder(country, osm_facilities),
            total_footprint_km2 = total_footprint_m2 / 1000000
          )

#bar chart for OSM Facility Counts
p1 <- ggplot(plot_data, aes(x = osm_facilities, y = country)) +
  geom_col(fill = palette_colors["primary"], width = 0.7) +
  labs(
    title = "OpenStreetMap Data Center Facility Counts",
    subtitle = "Top 12 countries ranked by crowdsourced object mapping volume",
    x = "Number of Mapped Facilities (OSM)",
    y = NULL
  ) +
  scale_x_continuous(labels = comma)

print(p1)
```

![](nsdc_project_files/figure-gfm/unnamed-chunk-4-1.png)<!-- -->

``` r
#filter top countries that i want labeled on the plot
labeled_countries <- c("United States of America", "France", "Germany", "United Kingdom", "Canada", "China", "Netherlands")

#only label the key points
label_df <- plot_data %>% filter(country %in% labeled_countries)

p2 <- ggplot(plot_data, aes(x = osm_facilities, y = median_footprint_m2, color = continent)) +
  geom_point(size = 4, alpha = 0.8) +
  #prevent overlapping
  geom_text(
    data = label_df,
    aes(label = country),
    size = 3,
    fontface = "bold",
    hjust = -0.1, #shift text slightly to the right of the dot
    vjust = 0.5,
    show.legend = FALSE
  ) +
  scale_color_manual(values = c(
    "Asia" = "#2B4C7E", 
    "Europe" = "#2A9D8F", 
    "North America" = "#E76F51", 
    "Oceania" = "#E9C46A"
  )) +
  labs(
    title = "Facility Count vs. Median Footprint Scale by Country",
    subtitle = "Comparing mapping volume against median facility footprint size (m²)",
    x = "OpenStreetMap Facility Count",
    y = "Median Footprint Area (m²)",
    color = "Continent"
  ) +
  scale_x_log10(labels = comma, limits = c(30, 4000)) + #expanded x-limits slightly to give labels room
  scale_y_log10(labels = comma)

print(p2)
```

![](nsdc_project_files/figure-gfm/unnamed-chunk-5-1.png)<!-- -->
