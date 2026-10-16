export { };

type Tool = "merge" | "divide";
type Entry = { file: File; pages?: number; error?: string };
const el = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
const form = el<HTMLFormElement>("pdf-form");
const input = el<HTMLInputElement>("file-input");
const submit = el<HTMLButtonElement>("submit");
const statusBox = el("status");
const pagesInput = el<HTMLInputElement>("pages");
const csrf = form.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")!.value;
let tool: Tool = "merge";
let entries: Entry[] = [];
let busy = false;
const megabytes = (bytes: number): string => `${(bytes / 1024 / 1024).toFixed(2)} MB`;

function status(message: string, error = false): void {
  statusBox.textContent = message;
  statusBox.className = error ? "error" : "success";
}

function render(): void {
  const list = el("file-list");
  list.replaceChildren();
  entries.forEach((entry, index) => {
    const row = document.createElement("li"); row.className = "file-row";
    const icon = document.createElement("span"); icon.className = "file-icon"; icon.textContent = "PDF";
    const info = document.createElement("div"); info.className = "file-info";
    const name = document.createElement("strong"); name.textContent = entry.file.name;
    const detail = document.createElement("small");
    detail.textContent = `${entry.error ?? (entry.pages === undefined ? "Comprobando PDF…" : `${entry.pages} páginas`)} · ${megabytes(entry.file.size)}`;
    info.append(name, detail);
    const actions = document.createElement("div"); actions.className = "file-actions";
    const addButton = (text: string, label: string, disabled: boolean, action: () => void): void => {
      const button = document.createElement("button"); button.type = "button"; button.textContent = text;
      button.setAttribute("aria-label", `${label}: ${entry.file.name}`); button.title = label; button.disabled = disabled || busy;
      button.addEventListener("click", action); actions.append(button);
    };
    if (tool === "merge") {
      addButton("↑", "Subir", index === 0, () => { [entries[index - 1], entries[index]] = [entries[index], entries[index - 1]]; render(); });
      addButton("↓", "Bajar", index === entries.length - 1, () => { [entries[index + 1], entries[index]] = [entries[index], entries[index + 1]]; render(); });
    }
    addButton("×", "Quitar", false, () => { entries.splice(index, 1); render(); });
    row.append(icon, info, actions); list.append(row);
  });
  el("empty").hidden = entries.length > 0;
  el("file-count").textContent = entries.length ? `${entries.length} archivo${entries.length === 1 ? "" : "s"} seleccionado${entries.length === 1 ? "" : "s"}` : "Ningún archivo seleccionado";
  el("summary-files").textContent = `${entries.length} PDF`;
  el("summary-size").textContent = megabytes(entries.reduce((sum, e) => sum + e.file.size, 0));
  const checked = entries.length > 0 && entries.every(e => e.pages !== undefined && !e.error);
  el("summary-pages").textContent = checked ? `${entries.reduce((sum, e) => sum + (e.pages ?? 0), 0)} páginas` : "—";
  const ready = checked && (tool === "merge" ? entries.length >= 2 : entries.length === 1);
  submit.disabled = busy || !ready;
  const mode = form.querySelector<HTMLInputElement>("[name=split-mode]:checked")!.value;
  submit.textContent = busy ? "Procesando…" : tool === "merge" ? "Unir archivos →" : mode === "extract" ? "Extraer páginas →" : "Separar y descargar ZIP →";
  el("ready-title").textContent = ready ? "Tus archivos están listos" : "Añade tus documentos";
  el("ready-detail").textContent = ready ? (tool === "merge" ? "Ajusta el orden con las flechas antes de unir." : "Elige cómo quieres separar las páginas.") : "Los PDF se comprobarán antes de continuar.";
  input.disabled = busy;
  el<HTMLButtonElement>("clear").disabled = busy || entries.length === 0;
  document.querySelectorAll<HTMLButtonElement>("[data-tool], #switch-tool").forEach(b => b.disabled = busy);
  form.querySelectorAll<HTMLInputElement>("[name=split-mode]").forEach(r => r.disabled = busy);
  pagesInput.disabled = busy || mode === "split";
}

function selectTool(next: Tool): void {
  if (busy || tool === next) return;
  tool = next; entries = []; input.value = ""; status("");
  document.querySelectorAll<HTMLButtonElement>("[data-tool]").forEach(b => b.classList.toggle("active", b.dataset.tool === tool));
  input.multiple = tool === "merge";
  el("split-options").hidden = tool === "merge";
  el("panel-title").textContent = tool === "merge" ? "Archivos para unir" : "Documento para dividir";
  el("panel-description").textContent = tool === "merge" ? "Añade dos o más archivos PDF y ordénalos como prefieras." : "Añade un PDF y elige las páginas que necesitas.";
  el("switch-tool").textContent = tool === "merge" ? "Ir a Dividir PDF →" : "Ir a Unir PDF →";
  render();
}

async function addFiles(files: File[]): Promise<void> {
  if (busy) return;
  status("");
  if (tool === "divide" && entries.length + files.length > 1) { status("Quita el documento actual y selecciona un único PDF para dividir.", true); return; }
  if (entries.length + files.length > 30 || [...entries.map(e => e.file), ...files].reduce((n, f) => n + f.size, 0) > Number(form.dataset.totalLimit) * 1024 * 1024) {
    status("La selección supera el límite de 30 archivos o el tamaño total permitido.", true); return;
  }
  if (files.some(f => !f.name.toLowerCase().endsWith(".pdf") || !f.size || f.size > Number(form.dataset.fileLimit) * 1024 * 1024)) {
    status(`Selecciona PDF no vacíos de hasta ${form.dataset.fileLimit} MB por archivo.`, true); return;
  }
  const added = files.map(file => ({ file } as Entry)); entries.push(...added); render();
  // Sequential requests avoid holding several large uploads in memory at once.
  for (const entry of added) {
    if (!entries.includes(entry)) continue;
    const data = new FormData(); data.append("files", entry.file);
    try {
      const response = await fetch("/inspeccionar/", { method: "POST", body: data, headers: { "X-CSRFToken": csrf } });
      const result = await response.json() as { pages?: number; error?: string };
      if (!response.ok || result.pages === undefined) throw new Error(result.error ?? "No se pudo comprobar el PDF.");
      entry.pages = result.pages;
    } catch (error) { entry.error = error instanceof Error ? error.message : "Error al comprobar el PDF."; }
    render();
  }
}
input.addEventListener("change", () => { void addFiles(Array.from(input.files ?? [])); input.value = ""; });
const dropzone = el("dropzone");
dropzone.addEventListener("dragover", event => { event.preventDefault(); if (!busy) dropzone.classList.add("over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("over"));
dropzone.addEventListener("drop", event => { event.preventDefault(); dropzone.classList.remove("over"); void addFiles(Array.from(event.dataTransfer?.files ?? [])); });
document.querySelectorAll<HTMLButtonElement>("[data-tool]").forEach(b => b.addEventListener("click", () => selectTool(b.dataset.tool as Tool)));
el("switch-tool").addEventListener("click", () => selectTool(tool === "merge" ? "divide" : "merge"));
el("clear").addEventListener("click", () => { entries = []; status(""); render(); });
form.querySelectorAll("[name=split-mode]").forEach(r => r.addEventListener("change", render));
form.addEventListener("submit", async event => {
  event.preventDefault(); if (busy || submit.disabled) return;
  const mode = form.querySelector<HTMLInputElement>("[name=split-mode]:checked")!.value;
  if (tool === "divide" && mode === "extract" && !pagesInput.value.trim()) { status("Indica las páginas que quieres extraer, por ejemplo: 1,3,5-8.", true); pagesInput.focus(); return; }
  const action = tool === "merge" ? "merge" : mode;
  const data = new FormData(); data.append("action", action); data.append("pages", pagesInput.value);
  entries.forEach(e => data.append("files", e.file)); busy = true; status("Procesando tus documentos…"); render();
  try {
    const response = await fetch(form.action, { method: "POST", body: data, headers: { "X-CSRFToken": csrf } });
    if (!response.ok) {
      const result = await response.json().catch(() => ({ error: "La carga fue rechazada por el servidor." })) as { error: string };
      throw new Error(result.error);
    }
    const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = action === "split" ? "kem-paginas.zip" : action === "merge" ? "kem-unido.pdf" : "kem-extraido.pdf";
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
    status("Listo. Tu descarga ha comenzado.");
  } catch (error) { status(error instanceof Error ? error.message : "Error de conexión. Vuelve a intentarlo.", true); }
  finally { busy = false; render(); }
});
render();
