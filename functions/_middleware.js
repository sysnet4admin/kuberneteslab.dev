export async function onRequest(context) {
  const { request, next } = context;
  const url = new URL(request.url);

  // Only redirect bare root; language-prefixed paths pass through as-is
  if (url.pathname !== "/") {
    return next();
  }

  const accept = request.headers.get("Accept-Language") || "";
  const preferred = accept.split(",")[0].trim().toLowerCase().split("-")[0];

  const target = preferred === "en" ? "/en/" : "/ko/";
  return Response.redirect(new URL(target, url.origin).href, 302);
}
