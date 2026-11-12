// docs/js/cv_parser.js

// URL do worker do PDF.js (necessário para ler o arquivo sem travar a tela)
const WORKER_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

// Função para normalizar texto (tira acentos, joga pra minúsculo e limpa símbolos)
function normText(text) {
    return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ");
}

export async function processarCurriculo(file, onProgress) {
    if (!window.pdfjsLib) {
        throw new Error("Biblioteca PDF.js não carregou.");
    }
    
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = WORKER_URL;
    onProgress("Lendo arquivo PDF...");

    // 1. Abre o PDF na memória do navegador
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await window.pdfjsLib.getDocument(arrayBuffer).promise;
    let fullText = "";

    // 2. Puxa o texto página por página
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        fullText += textContent.items.map(item => item.str).join(" ") + " ";
    }
    const normalizedPdf = normText(fullText);

    // 3. Puxa a peneira (skills.json) do seu próprio site
    onProgress("Comparando com as palavras-chave...");
    const skillsResponse = await fetch('./data/radar/skills.json');
    if (!skillsResponse.ok) throw new Error("Não achou o skills.json no frontend.");
    const skillsVocab = await skillsResponse.json();

    // 4. Faz o match: procura as skills da peneira no texto do seu currículo
    let mySkills = new Set();
    for (const [skillName, aliases] of Object.entries(skillsVocab)) {
        for (const alias of aliases) {
            const regex = new RegExp(`\\b${normText(alias)}\\b`);
            if (regex.test(normalizedPdf)) {
                mySkills.add(skillName);
                break; // Achou uma variação da skill, pula pra próxima
            }
        }
    }

    const finalSkills = Array.from(mySkills).sort();
    
    // 5. Salva o resultado no seu navegador
    localStorage.setItem('minhas_skills', JSON.stringify(finalSkills));
    return finalSkills;
}