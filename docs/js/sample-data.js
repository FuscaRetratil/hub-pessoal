/**
 * Dados de exemplo para o Radar de Vagas.
 * Utilizado como fallback caso o arquivo data/radar/jobs.json ainda não tenha sido gerado.
 */

var SRC = {
  gupy:    { name: 'Gupy',         url: 'https://portal.gupy.io/' },
  solides: { name: 'Sólides',      url: 'https://vagas.solides.com.br/' },
  google:  { name: 'Google Vagas', url: 'https://www.google.com/search?q=vagas+de+emprego&ibp=htl;jobs' }
};

var SRC_ORDER = ['gupy', 'solides', 'google'];

var LEVELS = ['Estágio', 'Trainee', 'Júnior', 'Pleno', 'Sênior', 'Não informado'];

function J(id, src, title, company, city, mode, level, area, days, reqs) {
  return { id: id, src: src, title: title, company: company, city: city, mode: mode, level: level, area: area, days: days, reqs: reqs };
}

var SAMPLE_JOBS = [
  J('g1','gupy','Estagiário de QA','Orbita Pagamentos','Recife','Presencial','Estágio','QA/Testes',0,['Testes manuais','Casos de teste','Jira','SQL','Noções de automação','Scrum']),
  J('go1','google','Estagiário de QA','Orbita Pagamentos','Recife','Presencial','Estágio','QA/Testes',0,['Testes manuais','Casos de teste','Jira','SQL','Noções de automação','Scrum']),
  J('g2','gupy','Analista de QA Júnior','Vértice Logística','Recife','Híbrido','Júnior','QA/Testes',1,['Selenium','Cypress','Python','Postman','API REST','Git','CI/CD','Jira']),
  J('go2','google','Analista de QA Júnior','Vértice Logística','Recife','Híbrido','Júnior','QA/Testes',1,['Selenium','Cypress','Python','Postman','API REST','Git','CI/CD','Jira']),
  J('s1','solides','QA Automation Jr','Nuvem Sul Tecnologia','Remoto','Remoto','Júnior','QA/Testes',1,['Cypress','JavaScript','Postman','Git','BDD','Docker','Jenkins']),
  J('g3','gupy','Desenvolvedor Frontend Júnior','Casa Digital','Recife','Híbrido','Júnior','Desenvolvimento',2,['React','JavaScript','TypeScript','HTML','CSS','Git','Testes unitários']),
  J('s2','solides','Estágio em Desenvolvimento Web','Faísca Software','Recife','Presencial','Estágio','Desenvolvimento',2,['JavaScript','HTML','CSS','Git','React']),
  J('g4','gupy','Analista de QA Sênior','Banco Meridional','Recife','Híbrido','Sênior','QA/Testes',0,['Estratégia de testes','Automação','Liderança técnica','Testes de performance','CI/CD','Python']),
  J('g5','gupy','Engenheiro de Testes Pleno','Argo Sistemas','São Paulo','Híbrido','Pleno','QA/Testes',3,['Automação','Java','Selenium','CI/CD','SQL']),
  J('s3','solides','QA Júnior','Praia Tech','Salvador','Presencial','Júnior','QA/Testes',3,['Testes manuais','Postman','SQL','Jira']),
  J('go3','google','Estagiário de Testes','Ônix Seguros','Fortaleza','Presencial','Estágio','QA/Testes',2,['Testes manuais','Casos de teste','Lógica de programação']),
  J('s4','solides','Estagiário de Marketing','Brisa Cosméticos','Recife','Presencial','Estágio','Marketing',1,['Redes sociais','Canva','Copywriting','Excel']),
  J('g6','gupy','Assistente Administrativo','Porto Grande Atacado','Recife','Presencial','Júnior','Administrativo',4,['Excel','Atendimento','Organização','Pacote Office']),
  J('go4','google','Desenvolvedor Backend Pleno','Nuvem Sul Tecnologia','Remoto','Remoto','Pleno','Desenvolvimento',2,['Node.js','SQL','Docker','API REST','AWS','Git']),
  J('s5','solides','Analista de Suporte Júnior','Tecelagem Digital','Recife','Presencial','Júnior','Suporte',3,['Atendimento','Linux','Redes','Help desk']),
  J('g7','gupy','Trainee em Tecnologia','Grupo Maré','Recife','Híbrido','Trainee','Desenvolvimento',5,['Lógica de programação','Python','SQL','Inglês']),
  J('go5','google','QA Engineer Jr (Mobile)','Alvorada Apps','Remoto','Remoto','Júnior','QA/Testes',4,['Appium','Android','Postman','Jira','Git','Testes de regressão']),
  J('s6','solides','Analista de Qualidade de Software','Rota Fácil','Jaboatão dos Guararapes','Presencial','Júnior','QA/Testes',5,['Testes funcionais','Casos de teste','SQL','Jira','Selenium']),
  J('g8','gupy','Desenvolvedor Full Stack Júnior','Caravela Labs','Remoto','Remoto','Júnior','Desenvolvimento',1,['React','Node.js','SQL','Git','API REST','TypeScript','Docker']),
  J('go6','google','Analista de Dados Júnior','Vila Dados','Recife','Híbrido','Júnior','Dados',3,['SQL','Python','Power BI','Excel','Estatística']),
  J('g9','gupy','Estágio em QA / Testes','Hélice Educação','Recife','Presencial','Estágio','QA/Testes',1,['Testes manuais','Documentação de testes','Lógica de programação','Python','Trabalho em equipe']),
  J('s7','solides','Analista de Testes Júnior','Zênite Telecom','Recife','Presencial','Júnior','QA/Testes',6,['Testes funcionais','Selenium','SQL','Linux','Jira','Casos de teste']),
  J('s8','solides','Designer de Produto Júnior','Faísca Software','Recife','Híbrido','Júnior','Design',2,['Figma','Prototipação','Design system','Pesquisa com usuários']),
  J('go7','google','Analista de QA Júnior','Quarta Onda','Remoto','Remoto','Júnior','QA/Testes',3,['Testes manuais','Cypress','Postman','SQL','Jira','Scrum'])
];
