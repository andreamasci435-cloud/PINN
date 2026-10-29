const byId = (id) => document.getElementById(id);
const safeUrl = (value) => {
  try {
    const url = new URL(value, location.origin);
    return url.protocol === "https:" ||
      (url.origin === location.origin && url.protocol === location.protocol)
      ? url.href
      : null;
  } catch {
    return null;
  }
};
function entries(id, items) {
  if (!Array.isArray(items) || !items.length) return;
  const root = byId(id);
  root.replaceChildren();
  for (const item of items) {
    const article = document.createElement("article");
    const date = document.createElement("span");
    date.className = "micro";
    date.textContent = item.dates || "";
    const title = document.createElement("h4");
    title.textContent = item.title || "";
    const institution = document.createElement("p");
    institution.textContent = item.institution || "";
    const detail = document.createElement("p");
    detail.textContent = item.description || "";
    article.append(date, title, institution, detail);
    root.append(article);
  }
}
try {
  const response = await fetch("/content/researcher.json", {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Profile unavailable");
  const author = await response.json();
  if (author.published) {
    byId("author-name").textContent = author.name || "Student profile";
    document.title = (author.name || "Student profile") + " — CANON";
    byId("profile-status").textContent =
      author.location || "RESEARCHER PROFILE";
    if (author.headline) byId("author-headline").textContent = author.headline;
    if (author.biography)
      byId("author-biography").textContent = author.biography;
    for (const field of ["education", "experience", "awards", "contributions"])
      entries(field + "-list", author[field]);
    if (author.skills?.length) {
      byId("skills-list").replaceChildren(
        ...author.skills.map((skill) => {
          const span = document.createElement("span");
          span.textContent = skill;
          return span;
        }),
      );
    }
    if (author.cv_url && safeUrl(author.cv_url)) {
      const link = byId("cv-link");
      link.href = safeUrl(author.cv_url);
      link.hidden = false;
      link.setAttribute("download", "");
      byId("cv-empty").hidden = true;
    }
    if (author.portrait_url && safeUrl(author.portrait_url)) {
      const image = byId("author-portrait");
      image.alt = author.name
        ? "Portrait of " + author.name
        : "Student portrait supplied for this profile";
      image.onload = () => {
        image.hidden = false;
        byId("portrait-placeholder").hidden = true;
      };
      image.src = safeUrl(author.portrait_url);
    }
    byId("author-links").replaceChildren();
    for (const item of author.links || []) {
      const url = safeUrl(item.url);
      if (url) {
        const a = document.createElement("a");
        a.href = url;
        a.textContent = item.label + " ↗";
        a.rel = "noreferrer";
        byId("author-links").append(a);
      }
    }
  }
} catch {
  byId("profile-status").textContent = "PROFILE DETAILS CURRENTLY UNAVAILABLE";
}
