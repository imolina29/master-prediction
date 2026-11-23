const API_BASE = process.env.API_BASE_URL || "http://localhost:8080";
const INTERNAL_KEY = process.env.INTERNAL_API_KEY || "";

export async function fetchAPI<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "X-Internal-Key": INTERNAL_KEY },
      next: { revalidate: 300 },
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  } catch {
    // Retry without cache to avoid serving stale errors
    try {
      const retry = await fetch(`${API_BASE}${path}`, {
        headers: { "X-Internal-Key": INTERNAL_KEY },
        cache: "no-store",
      });
      if (!retry.ok) return null;
      return retry.json();
    } catch {
      return null;
    }
  }
}
