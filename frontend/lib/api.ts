const API_BASE = process.env.API_BASE_URL || "http://localhost:8080";
const INTERNAL_KEY = process.env.INTERNAL_API_KEY || "";

export async function fetchAPI<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "X-Internal-Key": INTERNAL_KEY },
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
