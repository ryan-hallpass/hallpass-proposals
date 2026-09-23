# Hallpass proposal template

One template, one data file per city. Every page lives at `proposals.hallpassdigital.com/<slug>`.

```
david-proposals-deploy/            ← site root (deployed to Vercel)
  assets/                          ← SHARED fixed assets: Hallpass logo, client logos, Andy Lennon photo, favicon
  davis/                           ← generated page + that city's photos and share image
  _template/                       ← NOT deployed (see .vercelignore)
    template.html                  ← the locked page layout (Jinja template)
    build.py                       ← builds a city page from its brief
    cities/davis.json              ← reference brief — copy this for each new city
  _src/                            ← NOT deployed: working files, old versions, Muse prompt
```

## New city, start to finish

1. Run the Muse prompt (`_src/muse-proposal-prompt.md`) for the city. Muse returns a Markdown content brief.
2. Claude converts the brief into `_template/cities/<slug>.json`, using `davis.json` as the model.
3. From the site root: `python3 _template/build.py _template/cities/<slug>.json`
   - downloads the photos into `<slug>/assets/`
   - writes `<slug>/index.html`
   - renders the share image `<slug>/assets/og.jpg` (needs Playwright; add `--no-og` to skip)
4. Review the page, then deploy: `vercel deploy --prod`

## What's fixed vs. custom

**Fixed in `template.html`** (edit there once and it changes every future build):
track record strip and client logos · point-of-view copy · Ardmore case study, chart, and videos · Andy Lennon testimonial · report structure · capabilities grid · $9,500 anchor and budget line · booking link · noindex tags · analytics.

**Custom per city, in the JSON:**

| JSON field | What it is |
|---|---|
| `slug`, `city_name`, `city_full`, `prepared_date`, `contact_name` | Basics. `contact_name` fills "A focused two-minute read for …" (leave empty to hide the line) |
| `hero.headline` | Wrap one word in `*asterisks*` to turn it orange |
| `hero.lead`, `hero.photo {src, alt}`, `hero.photo_tag` | `src` can be a URL (downloaded at build) or a local path |
| `concepts.headline`, `concepts.lead` | Section 01 |
| `concepts.series[2]` | `label`, `title`, `description`, `photo` for each illustrative series |
| `concepts.social` | Mock post: `account`, `location`, `handle`, `caption`, `photo` (`avatar` letter optional) |
| `plan.quote` | Verbatim quote; wrap the pillar phrase in `*asterisks*` for teal bold |
| `plan.quote_source` | Plan name + approval date |
| `plan.outside_help_quote` | Optional; the callout box is hidden if empty |
| `pov.people_line`, `pov.photo`, `pov.caption` | Candid local photo beside "Made to be watched" |
| `scale_target` | Their numeric target, e.g. "25,000+ impressions a year"; the "For scale" line is hidden if empty |
| `report.title_line1`, `report.pillars` | Board-report mock |
| `journey.audiences`, `journey.step1`, `journey.step3` | Funnel targets |
| `deliverables.launch` (3), `deliverables.monthly` (4) | Short bullets; a trailing "(parenthetical)" renders as a small aside |
| `cta_headline` | Optional; defaults to "Let's put {City}'s story to work for its economic goals." |
| `footer.sources_html`, `footer.photo_credits_html` | Plan link and photo credits (HTML allowed) |

## Rules that keep it honest
- Quotes are verbatim, with the source linked in the footer.
- Real photos only, credited; ask permission when a photo isn't openly licensed.
- Fixed numbers (900M+, 1.4M+, +108%, 98K) change only in `template.html`, and only when they change on hallpassdigital.com.
