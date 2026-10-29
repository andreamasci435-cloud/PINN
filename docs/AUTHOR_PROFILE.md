# Researcher profile and CV

The page `/researcher.html` is ready, in the same visual system as the laboratory. It deliberately contains no invented identity, school, award, affiliation, portrait or contact address.

Edit `web/content/researcher.json` when approved information is available. Set `published` to true and provide a nonempty `name` to enable the personal content. This flag controls rendering only: **the JSON itself is a public static asset**, so it must never contain private draft information.

Fields:

- `name`, `headline`, `biography`, `location`: plain text.
- `education`, `experience`, `awards`, `contributions`: arrays of objects with `dates`, `title`, `institution`, `description`.
- `skills`: array of plain-text strings.
- `links`: array of objects with `label`, `url` (HTTPS or a same-origin URL).
- `cv_url`: path such as `/content/cv.pdf`, after adding the real PDF under `web/content/`.
- `portrait_url`: path such as `/content/portrait.jpg`, after supplying a licensed/authorized portrait.

A neutral entry template, to replace with verified facts:

```json
{
  "dates": "",
  "title": "",
  "institution": "",
  "description": ""
}
```

Refresh the page after editing. The CV button remains hidden until a link is supplied. Blank sections retain clear placeholders. Text is inserted as text, not executable HTML.

The contributions section should accurately describe who designed the experiment, wrote or reviewed code, analyzed results, acquired measurements and prepared visualizations. Explain AI assistance where applicable; do not imply that all implemented work or numerical experiments were independently performed by the student. A project page is not evidence of authorship until that attribution is completed.
