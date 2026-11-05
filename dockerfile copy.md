docker build -t meu-reflex .

docker run --rm -p 3000:3000 meu-reflex

docker run --rm --env-file .env -v "${PWD}:/app" meu-reflex python scripts/enviar_email_teste.py --para mateus.dotta@aluno.impacta.edu.br
