const POST_LOGIN_PATH_KEY = "postLoginPath";

export function rememberPostLoginPath(path: string) {
  try {
    if (path.startsWith("/") && !path.startsWith("//")) {
      sessionStorage.setItem(POST_LOGIN_PATH_KEY, path);
    }
  } catch {
    return;
  }
}

export function takePostLoginPath(): string {
  try {
    const path = sessionStorage.getItem(POST_LOGIN_PATH_KEY);
    sessionStorage.removeItem(POST_LOGIN_PATH_KEY);
    if (path && path.startsWith("/") && !path.startsWith("//")) {
      return path;
    }
  } catch {
    return "/networth";
  }
  return "/networth";
}
