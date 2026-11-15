# Public Frontend for Master Prediction

## Intent

Master Prediction is a sports analytics platform that generates match predictions for European football using XGBoost ML models. It currently runs as a private NiceGUI dashboard behind login. The goal is to make predictions and analytics publicly available on the internet so anyone searching for match predictions can find and use them. The owner retains full control of the private admin dashboard, model training, and prediction generation.

### Why now

The prediction model is stable (52.8% overall, 82.1% on high-confidence picks across 615 resolved predictions). The dashboard is complete and functional. There are no more users to get — the product needs to be found.

### Success criteria

- A public website indexed by Google for queries like "predicciones Premier League", "pronósticos fútbol europeo"
- Server-side rendered pages that load fast and are crawlable
- Visitors see upcoming predictions with useful context (probabilities, team stats, form) without creating an account
- Track record is transparent and verifiable
- Structure is ready for monetization (ad slots, affiliate placeholders) without implementing them yet
- The existing private dashboard continues to work unchanged

### Anti-goals

- This is NOT a betting site. No odds comparison, no "best bet" labels, no stake suggestions
- No user accounts, login, or personalization in the MVP
- No chat/advisor feature publicly (stays private)
- No real-time live scores or match tracking
- No mobile app — responsive web only

## Architecture

### Two services, one repository

```
golpredictor/
├── backend/          # Existing Python backend (unchanged except new public API routes)
├── webapp/           # Existing NiceGUI dashboard (unchanged)
├── frontend/         # NEW: Next.js public site
├── scripts/          # Existing ML scripts (unchanged)
├── data/             # Existing data files (unchanged)
└── Dockerfile        # Existing Railway Dockerfile for Python service
```

**Python service** (existing, on Railway): Serves the NiceGUI dashboard on port 8080 and exposes new public API endpoints under `/api/public/`. No authentication required for public endpoints. The existing authenticated endpoints (`/api/chat`, `/api/performance`) stay unchanged.

**Next.js service** (new, on Railway): Serves the public website. Calls the Python service's public API internally on Railway's private network. Deployed as a second Railway service in the same project.

### Public API endpoints (added to existing FastAPI)

All under `/api/public/`, no authentication:

1. `GET /api/public/predictions/upcoming` — Next 21 days of predictions with probabilities, confidence, division
2. `GET /api/public/predictions/track-record` — Resolved predictions with actual results, paginated
3. `GET /api/public/predictions/stats` — Aggregate accuracy stats (overall, by confidence, by division)
4. `GET /api/public/match/{date}/{home_team}/{away_team}` — Single match detail with team features (goals avg, xG, win rate, form, ELO, H2H)
5. `GET /api/public/league/{division}/upcoming` — Upcoming predictions filtered by league
6. `GET /api/public/health` — Simple health check

Rate limiting: 60 requests/minute per IP using slowapi, to prevent scraping. Internal requests from the Next.js service are exempt via a shared `X-Internal-Key` header (environment variable shared between both services), so ISR revalidation and sitemap generation are never throttled.

### Available data inventory

**Parquet features file** (`data/features/team_features.parquet`, baked into Docker image at deploy, updated by CI commits with `[no deploy]` tag — the image is rebuilt on each actual deploy):
- Season averages: `goals_scored_avg`, `goals_conceded_avg`, `xg_for_avg`, `xg_against_avg`, `shots_target_avg`, `win_rate`, `draw_rate`, `btts_rate`, `over25_rate`, `xg_diff_avg`, `xg_overperformance`
- Last 3 match form: `goals_scored_avg_3`, `goals_conceded_avg_3`, `win_rate_3`
- Last 10 match form: `goals_scored_avg_10`, `goals_conceded_avg_10`, `win_rate_10`
- Venue-specific: `venue_win_rate`, `venue_goals_avg`
- Position and H2H: `league_pos`, `h2h_win_rate`, `h2h_avg_goals`, `h2h_matches`
- Context: `rest_days`

**Supabase `predictions` table**: `match_date`, `home_team`, `away_team`, `division`, `prob_home`, `prob_draw`, `prob_away`, `prob_over25`, `prob_btts`, `predicted_result`, `confidence`

**Supabase `matches` table**: `home_elo`, `away_elo`, `ft_result`, `ft_home_goals`, `ft_away_goals`, plus detailed match stats (shots, corners, cards)

**Note on Champions League**: CL uses division code `"EC"`. It has ELO ratings (domestic ELO + league strength bonus) but `league_pos` is not meaningful for CL. The match detail template should gracefully omit league position for CL matches. All other features are available.

### Slug mapping

Team slugs are generated deterministically by lowercasing, replacing spaces with hyphens, and removing accents (e.g., "Real Madrid" → `real-madrid`, "Atlético Madrid" → `atletico-madrid`). The API accepts both the slug form and the original team name. Division-to-slug mapping is a fixed dictionary:

| Division code | Slug | Display name |
|---|---|---|
| E0 | premier-league | Premier League |
| SP1 | la-liga | La Liga |
| I1 | serie-a | Serie A |
| D1 | bundesliga | Bundesliga |
| F1 | ligue-1 | Ligue 1 |
| EC | champions-league | Champions League |

### Data flow

```
Supabase (predictions, matches tables)
    ↓
Python backend (public API endpoints read from Supabase + parquet features)
    ↓ Railway private network
Next.js (SSR fetches data at request time, renders HTML)
    ↓
User's browser (fully rendered HTML, SEO-friendly)
```

### SEO strategy

- Server-side rendering for all pages (no client-only data fetching for primary content)
- Semantic HTML with structured data (JSON-LD for SportsEvent)
- Dynamic sitemap.xml generated from available leagues and upcoming matches
- Meta tags with Open Graph for social sharing
- Spanish language (`lang="es"`) — primary audience is Spanish-speaking
- Clean URLs: `/liga/premier-league`, `/partido/2026-11-21/real-madrid-vs-celta-vigo`

## Pages

### 1. Home (`/`)

The landing page. Shows:

- **Hero section**: Headline "Predicciones de Fútbol Europeo con Inteligencia Artificial", brief description, track record summary (615+ partidos analizados, 82% precisión alta confianza)
- **Partidos Destacados**: Top 6 upcoming matches sorted by confidence (alta first, then by date). Each card shows: teams, league badge, date, predicted result with probability bar, confidence level badge
- **Track Record section**: Overall accuracy number, accuracy by confidence tier (alta/media/baja), number of predictions resolved
- **Ligas section**: Cards for each league (Premier, La Liga, Serie A, Bundesliga, Ligue 1, Champions League) linking to league pages
- **Disclaimer footer**: "Análisis informativo. Las decisiones de apuesta son responsabilidad exclusiva del usuario."

### 2. Match detail (`/partido/[date]/[slug]`)

Individual match analysis page. The richest page — this is where Google queries like "prediccion Real Madrid vs Celta" should land.

- **Header**: Teams, league, date/time, predicted result with confidence badge
- **Probability breakdown**: Visual bars for H/D/A probabilities
- **Team comparison table**: Side-by-side stats
  - ELO rating (with who has advantage)
  - Goals scored avg (season + last 3)
  - Goals conceded avg (season + last 3)
  - Win rate (season + last 3)
  - xG for/against averages
  - BTTS rate, Over 2.5 rate
  - League position
  - H2H record if available
- **Ventajas section**: Auto-generated bullets from comparing the two teams' feature data. Rules: compare goals_scored_avg, goals_conceded_avg, win_rate, xg_diff_avg, venue_win_rate, and h2h_win_rate. Generate 2-3 bullets per team highlighting where they have a clear statistical edge (e.g., "Real Madrid promedia 2.1 goles por partido en casa", "Celta concede 1.8 goles por partido fuera"). No SHAP or per-prediction feature importance — purely statistical comparison.
- **Model confidence explanation**: A short text explaining what "alta/media/baja" means in terms of historical accuracy (e.g., "Confianza alta: el modelo acierta el 82% de estas predicciones"). No per-feature importance — that data is not stored per prediction.
- **Disclaimer**: Same betting responsibility notice

### 3. League page (`/liga/[slug]`)

All upcoming predictions for one league.

- **League header**: Name, flag/badge, season
- **Predictions table/cards**: All upcoming matches for this league, each showing teams, date, predicted result, confidence, H/D/A probabilities
- **League Track Record**: Accuracy for this specific league
- Links to each match detail page

League slugs: `premier-league`, `la-liga`, `serie-a`, `bundesliga`, `ligue-1`, `champions-league`

### 4. Track Record (`/track-record`)

Transparency page — verifiable history.

- **Summary stats**: Total predictions, overall accuracy, by confidence tier
- **By league breakdown**: Table with accuracy per league
- **Recent results**: Paginated list of last N resolved predictions showing: match, predicted result, actual result, correct/incorrect badge, confidence, date
- Filterable by league and confidence

### 5. Static pages

- `/about` — What is Master Prediction, how the model works (high level: "modelo de machine learning entrenado con datos históricos de más de 100,000 partidos"), single-person project credit. Builder writes the copy in Spanish.
- `/disclaimer` — Full legal disclaimer: analysis is informational only, not betting advice, no liability for losses, user assumes all risk. Builder writes standard Spanish-language disclaimer copy.

### SEO and crawling

- The Next.js public site is fully indexable. `robots.txt` allows all crawlers.
- The NiceGUI dashboard (`app.` subdomain) gets `robots.txt` with `Disallow: /` to prevent indexing.
- `/api/public/` routes are blocked from crawlers via `robots.txt` on the Python service.
- `sitemap.xml` is generated dynamically by Next.js from the list of leagues and upcoming matches.

### Empty states

- **No upcoming matches** (international break): Show "No hay partidos programados próximamente. Vuelve pronto." with the track record section still visible.
- **Match with missing features**: Omit the missing rows from the comparison table; show only what's available. Never show "N/A" rows.
- **API unreachable**: Show cached content if available (ISR), otherwise a friendly "Datos temporalmente no disponibles" message.
- **Hero numbers**: Live from `/api/public/predictions/stats`, not hardcoded. They update as new predictions resolve.

## Design

### Visual identity

- **Character**: Data-driven, trustworthy, sharp. Not flashy or gambling-themed
- **Palette**: Dark theme (near-black background `#0a0a0a`), white text, one accent color — a muted amber/gold `#d4a017` for confidence highlights and key numbers. League-specific accent colors for badges only
- **Typography**: Inter for UI, tabular-nums for probabilities and stats
- **Layout**: Full-width responsive, max-width 1200px content area, generous spacing
- **Cards**: Subtle border (`#1a1a1a`), slight surface elevation for match cards
- **No**: gradients, glows, betting imagery, money symbols, slot-machine aesthetics

### Responsive behavior

- Desktop: Grid layouts, side-by-side team comparisons
- Tablet: Stacked where needed, grid reduces to 2 columns
- Mobile: Single column, cards stack, team comparison becomes vertical

## Deployment

### Railway configuration

Two services in the same Railway project:

1. **master-prediction-api** (existing): Python service, port 8080, serves NiceGUI + API
2. **master-prediction-web** (new): Next.js service, port 3000, public-facing

Railway private networking allows the Next.js service to call the Python API without going through the public internet.

### Environment variables (Next.js service)

- `API_BASE_URL` — Internal Railway URL of the Python service (e.g., `http://master-prediction-api.railway.internal:8080`)
- `NEXT_PUBLIC_SITE_URL` — Public URL of the site (the custom domain)

### Custom domain

The user will purchase and configure a custom domain. Railway handles SSL automatically. Setup:

- `www.masterprediction.com` (or chosen domain) → Next.js service
- `app.masterprediction.com` → Python service (existing NiceGUI dashboard, behind login)
- `api.masterprediction.com` → Python service `/api/` routes (optional, for future third-party integrations)

Domain choice is the user's decision; the architecture works with any domain.

### Dockerfile (Next.js)

Standard Next.js standalone output build:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

## Constraints

- **Language**: All user-facing text in Spanish
- **No new database**: All data comes from existing Supabase tables and parquet files via the Python API
- **No breaking changes**: The existing NiceGUI dashboard, API endpoints, and ML pipeline must continue working unchanged
- **Minimal dependencies**: Next.js 14, Tailwind CSS, and nothing else on the frontend. No UI component libraries
- **Performance**: Pages must load in under 2 seconds. All pages use ISR (Incremental Static Regeneration) with `revalidate = 300` (5 minutes). No build-time static generation (`generateStaticParams` returns empty) because the API is unreachable during Docker build on Railway. Pages render on first request and are then cached. If the API is down, pages show a "datos temporalmente no disponibles" message, not a 500 error.
- **Budget**: Railway Hobby plan ($5/month) supports multiple services. No additional paid services

## Monetization-ready structure (not implemented in MVP)

- Reserved `<div>` slots in layout for future ad placement (sidebar, between match cards, footer)
- Affiliate link component exists but renders nothing until configured
- UTM parameter tracking on outbound links
- Analytics-ready: Google Analytics 4 script slot in layout (not activated until user provides GA ID)

## Out of scope

- User registration / authentication on public site
- Push notifications
- Live scores
- Social features (comments, sharing predictions)
- Payment processing
- Email newsletter signup (future phase)
- Multi-language support (Spanish only for now)
