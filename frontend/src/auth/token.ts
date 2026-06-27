// Where the JWT lives in the browser. localStorage keeps the user logged in
// across reloads. (Trade-off note for the interview: localStorage is simple but
// readable by JS, so it's XSS-exposed; a hardened app would use an httpOnly
// cookie. Fine for this demo — see docs/adr/0001 next steps.)
const TOKEN_KEY = "documind_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}
