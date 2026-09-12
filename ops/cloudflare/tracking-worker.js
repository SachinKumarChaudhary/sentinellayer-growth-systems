export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/t/')) return fetch(request);

    const token = url.pathname.slice(3).split('/')[0];
    if (!/^[A-Za-z0-9_-]{20,128}$/.test(token)) {
      return new Response('Not Found', { status: 404 });
    }

    const upstream = new URL(env.TRACKING_ORIGIN);
    upstream.pathname = `/t/${token}`;
    upstream.search = url.search;

    const headers = new Headers(request.headers);
    headers.set('X-SL-Edge', 'cloudflare-worker');
    headers.set('X-Forwarded-Proto', 'https');
    headers.set('X-Forwarded-Host', url.host);

    const response = await fetch(new Request(upstream.toString(), {
      method: request.method,
      headers,
      redirect: 'manual',
    }));

    const out = new Response(response.body, response);
    out.headers.set('Cache-Control', 'no-store');
    return out;
  },
};
