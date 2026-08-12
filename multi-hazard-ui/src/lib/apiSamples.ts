export type SampleRequest = {
  method: string;
  url: string;
};

export function buildCurlSample({ method, url }: SampleRequest): string {
  const flag = method.toUpperCase() === "GET" ? "" : ` -X ${method.toUpperCase()}`;
  return `curl${flag} "${url}"`;
}

export function buildFetchSample({ method, url }: SampleRequest): string {
  const methodLine = method.toUpperCase() === "GET" ? "" : `, { method: "${method.toUpperCase()}" }`;
  return `fetch("${url}"${methodLine})\n  .then((res) => res.json())\n  .then((data) => console.log(data));`;
}

export function buildPythonSample({ method, url }: SampleRequest): string {
  const call = method.toUpperCase() === "GET" ? "requests.get" : `requests.request`;
  const args = method.toUpperCase() === "GET" ? `"${url}"` : `"${method.toUpperCase()}", "${url}"`;
  return `import requests\n\nresponse = ${call}(${args})\nprint(response.json())`;
}
