/**
 * Motores de Match do Radar de Vagas.
 * 
 * Contrato de um motor:
 *   (job, resume) -> { have: list[str], missing: list[str], total: int, pct: int, method: str }
 * 
 * O motor padrão é baseado em palavras-chave e sinônimos (ALIASES).
 * No futuro (Fase 7), basta implementar e plugar a função em ENGINES.ai.
 */

function norm(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}
window.norm = norm;

var ALIASES = {
  'api rest': ['api', 'apis', 'rest', 'restful'],
  'ci/cd': ['ci', 'cd', 'jenkins', 'github actions', 'gitlab ci', 'pipeline', 'pipelines'],
  'testes funcionais': ['teste funcional', 'testes manuais', 'teste manual'],
  'casos de teste': ['teste manual', 'testes manuais', 'documentacao de testes', 'plano de testes'],
  'testes manuais': ['teste manual', 'testes funcionais'],
  'testes de regressao': ['regressao', 'teste de regressao'],
  'testes automatizados': ['automacao', 'automacao de testes', 'test automation', 'selenium', 'cypress', 'playwright'],
  'testes de api': ['teste de api', 'testes de apis', 'teste de apis', 'postman', 'rest'],
  'testes de performance': ['teste de performance', 'testes de carga', 'teste de carga', 'k6', 'jmeter', 'gatling'],
  'node.js': ['node', 'nodejs'],
  'nocoes de automacao': ['automacao', 'selenium', 'cypress', 'playwright'],
  'logica de programacao': ['programacao', 'python', 'javascript'],
  'testes unitarios': ['jest', 'vitest', 'unittest', 'pytest'],
  'bdd': ['cucumber', 'gherkin']
};

function parseSkills(text) {
  return text.split(/[,;\n]/).map(norm).filter(Boolean);
}

function keywordMatch(job, resume) {
  var skills = resume.skills || [];
  var have = [];
  var missing = [];

  (job.reqs || []).forEach(function(req) {
    var r = norm(req);
    var cands = [r].concat(ALIASES[r] || []);
    var ok = skills.some(function(s) {
      return cands.some(function(c) {
        return s === c || (c.length >= 4 && s.indexOf(c) >= 0) || (s.length >= 4 && c.indexOf(s) >= 0);
      });
    });
    (ok ? have : missing).push(req);
  });

  var total = (job.reqs || []).length;
  var pct = total ? Math.round(100 * have.length / total) : 0;

  return {
    have: have,
    missing: missing,
    total: total,
    pct: pct,
    method: 'keywords'
  };
}

var ENGINES = {
  keywords: keywordMatch,
  ai: null
};

function runMatch(job, state) {
  var engineName = state && state.engine ? state.engine : 'keywords';
  var fn = ENGINES[engineName] || ENGINES.keywords;
  var skillsText = state && state.skills ? state.skills : '';
  return fn(job, { skills: parseSkills(skillsText) });
}
