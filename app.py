from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import sqlite3
import hashlib
from datetime import timedelta
from fpdf import FPDF
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessao'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'

# Função para conectar ao banco de moderadores
def get_auth_db():
    conn = sqlite3.connect('database/cmob_moderadores.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para conectar ao banco de colaboradores
def get_colab_db():
    conn = sqlite3.connect('database/colaboradores.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para verificar credenciais - VERSÃO CORRIGIDA
def check_credentials(username, password):
    try:
        conn = get_auth_db()
        c = conn.cursor()
        c.execute("SELECT * FROM moderadores WHERE usuario=?", (username,))
        moderador = c.fetchone()
        conn.close()

        if moderador:
            senha_hash = moderador['senha_hash']  # Alterado de 'senha' para 'senha_hash'
            senha_input_hash = hashlib.sha256(password.encode()).hexdigest()
            return senha_input_hash == senha_hash
        return False
    except Exception as e:
        app.logger.error(f"Erro ao verificar credenciais: {str(e)}")
        return False

# Função para buscar funcionário
def get_funcionario_by_search(search_value):
    try:
        conn = get_colab_db()
        c = conn.cursor()
        c.execute("SELECT * FROM funcionarios WHERE cpf = ? OR matricula = ?", 
                (search_value, search_value))
        funcionario = c.fetchone()
        conn.close()
        return funcionario
    except Exception as e:
        app.logger.error(f"Erro ao buscar funcionário: {str(e)}")
        return None

# Função para gerar PDF
def gerar_pdf(funcionario, filename):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Dados do Funcionário", ln=True, align="C")
        pdf.ln(10)

        # Mapeamento de campos (nome_original: nome_exibicao)
        campos = {
            'nome': 'Nome',
            'data_nascimento': 'Data Nascimento',
            'cpf': 'CPF',
            'rg': 'RG',
            'orgao_emissor': 'Órgão Emissor',
            'estado_civil': 'Estado Civil',
            'nacionalidade': 'Nacionalidade',
            'nome_mae': 'Nome da Mãe',
            'nome_pai': 'Nome do Pai',
            'endereco': 'Endereço',
            'telefone': 'Telefone',
            'email': 'Email',
            'cargo': 'Cargo',
            'departamento': 'Departamento',
            'data_admissao': 'Data Admissão',
            'matricula': 'Matrícula',
            'tipo_contrato': 'Tipo de Contrato',
            'salario_base': 'Salário Base',
            'banco': 'Banco',
            'agencia': 'Agência',
            'conta': 'Conta',
            'carteira_trabalho_numero': 'CTPS Número',
            'carteira_trabalho_serie': 'CTPS Série',
            'carteira_trabalho_data_emissao': 'CTPS Data Emissão',
            'escolaridade': 'Escolaridade',
            'cursos_relevantes': 'Cursos Relevantes',
            'certificacoes': 'Certificações',
            'historico_profissional': 'Histórico Profissional'
        }

        for campo_banco, label in campos.items():
            valor = funcionario[campo_banco] if funcionario[campo_banco] is not None else ''
            pdf.cell(200, 10, txt=f"{label}: {valor}", ln=True)

        os.makedirs('static/pdfs', exist_ok=True)
        output_path = os.path.join('static/pdfs', filename)
        pdf.output(output_path)
        return output_path
    except Exception as e:
        app.logger.error(f"Erro ao gerar PDF: {str(e)}")
        return None

# Rotas de autenticação
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('auth.html', error="Preencha todos os campos")
        
        if check_credentials(username, password):
            session['username'] = username
            session.permanent = True
            return redirect(url_for('main'))
        
        return render_template('auth.html', error="Credenciais inválidas")
    
    return render_template('auth.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Rotas principais
@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('main.html', username=session['username'])

@app.route('/visualizar_funcionarios')
def visualizar_funcionarios():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('visualizar_funcionarios.html', username=session['username'])

@app.route('/buscar_funcionario', methods=['GET'])
def buscar_funcionario():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Não autenticado'}), 401

    search_value = request.args.get('search_value')
    if not search_value:
        return jsonify({'status': 'error', 'message': 'Informe um CPF ou matrícula'}), 400

    try:
        funcionario = get_funcionario_by_search(search_value)
        if not funcionario:
            return jsonify({'status': 'error', 'message': 'Funcionário não encontrado'}), 404

        pdf_filename = f"{funcionario['nome'].replace(' ', '_')}_dados.pdf"
        pdf_path = gerar_pdf(funcionario, pdf_filename)
        
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({'status': 'error', 'message': 'Erro ao gerar PDF'}), 500
            
        pdf_url = url_for('static', filename=f'pdfs/{pdf_filename}')
        
        return jsonify({
            'status': 'success',
            'message': f'Funcionário encontrado: {funcionario["nome"]}',
            'pdf_url': pdf_url
        })
    except Exception as e:
        app.logger.error(f"Erro na rota buscar_funcionario: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Erro interno'}), 500

@app.route('/baixar_dados')
def baixar_dados():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    cpf = request.args.get('cpf')
    if not cpf:
        return "CPF não fornecido", 400

    try:
        funcionario = get_funcionario_by_search(cpf)
        if not funcionario:
            return "Funcionário não encontrado", 404

        pdf_filename = f"{funcionario['nome'].replace(' ', '_')}_dados.pdf"
        pdf_path = os.path.join('static/pdfs', pdf_filename)
        
        if os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True)
        return "Arquivo não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar dados: {str(e)}")
        return "Erro interno", 500

# Rotas de gestão de colaboradores
@app.route('/add-funcionario', methods=['GET', 'POST'])
def add_funcionario():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        required_fields = ['nome', 'cpf', 'matricula']
        for field in required_fields:
            if not request.form.get(field):
                return render_template('add_funcionario.html',
                                    username=session['username'],
                                    error=f"Campo {field} é obrigatório")

        try:
            conn = get_colab_db()
            cursor = conn.cursor()

            fields = [
                'nome', 'data_nascimento', 'cpf', 'rg', 'orgao_emissor',
                'estado_civil', 'nacionalidade', 'nome_mae', 'nome_pai',
                'endereco', 'telefone', 'email', 'cargo', 'departamento',
                'data_admissao', 'matricula', 'tipo_contrato', 'salario_base',
                'banco', 'agencia', 'conta', 'carteira_trabalho_numero', 
                'carteira_trabalho_serie', 'carteira_trabalho_data_emissao',
                'escolaridade', 'cursos_relevantes', 'certificacoes', 
                'historico_profissional'
            ]

            values = [request.form.get(field, '').strip() or None for field in fields]
            
            placeholders = ','.join(['?'] * len(fields))
            query = f"INSERT INTO funcionarios ({','.join(fields)}) VALUES ({placeholders})"
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            return redirect(url_for('main'))
        
        except sqlite3.IntegrityError:
            return render_template('add_funcionario.html',
                                username=session['username'],
                                error="CPF ou matrícula já cadastrado")
        
        except Exception as e:
            app.logger.error(f"Erro ao adicionar funcionário: {str(e)}")
            return render_template('add_funcionario.html',
                                username=session['username'],
                                error="Erro ao cadastrar")

    return render_template('add_funcionario.html', username=session['username'])

@app.route('/edit_funcionario', methods=['GET', 'POST'])
def edit_funcionario():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        search_value = request.form.get('search_value')
        if not search_value:
            return render_template('edit_funcionario.html',
                                username=session['username'],
                                error="Informe um CPF ou matrícula")

        funcionario = get_funcionario_by_search(search_value)
        if not funcionario:
            return render_template('edit_funcionario.html',
                                username=session['username'],
                                error="Funcionário não encontrado",
                                search_value=search_value)

        return render_template('edit_funcionario.html',
                            username=session['username'],
                            funcionario=funcionario,
                            search_value=search_value)

    return render_template('edit_funcionario.html', username=session['username'])

@app.route('/atualizar_funcionario', methods=['POST'])
def atualizar_funcionario():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Obter CPF para manter o contexto de pesquisa
    cpf = request.form.get('cpf', '')
    
    try:
        # Verificar ID do funcionário
        funcionario_id = request.form.get('id')
        if not funcionario_id:
            return redirect(url_for('edit_funcionario',
                                error="ID do funcionário não especificado",
                                search_value=cpf))

        # Conectar ao banco
        conn = get_colab_db()
        cursor = conn.cursor()

        # Verificar se funcionário existe
        cursor.execute("SELECT id FROM funcionarios WHERE id = ?", (funcionario_id,))
        if not cursor.fetchone():
            conn.close()
            return redirect(url_for('edit_funcionario',
                                error="Funcionário não encontrado",
                                search_value=cpf))

        # Lista de campos permitidos para atualização
        campos_permitidos = {
            'nome': str,
            'data_nascimento': str,
            'rg': str,
            'orgao_emissor': str,
            'estado_civil': str,
            'nacionalidade': str,
            'nome_mae': str,
            'nome_pai': str,
            'endereco': str,
            'telefone': str,
            'email': str,
            'cargo': str,
            'departamento': str,
            'data_admissao': str,
            'tipo_contrato': str,
            'salario_base': float,
            'banco': str,
            'agencia': str,
            'conta': str,
            'carteira_trabalho_numero': str,
            'carteira_trabalho_serie': str,
            'carteira_trabalho_data_emissao': str,
            'escolaridade': str,
            'cursos_relevantes': str,
            'certificacoes': str,
            'historico_profissional': str
        }

        # Preparar dados para atualização
        updates = []
        valores = []
        
        for campo, tipo in campos_permitidos.items():
            if campo in request.form:
                try:
                    valor = request.form[campo].strip()
                    # Converter para o tipo esperado
                    if tipo == float:
                        valor = float(valor) if valor else None
                    elif tipo == str:
                        valor = valor if valor else None
                    
                    updates.append(f"{campo} = ?")
                    valores.append(valor)
                except ValueError:
                    conn.close()
                    return redirect(url_for('edit_funcionario',
                                        error=f"Formato inválido para {campo}",
                                        search_value=cpf))

        if not updates:
            conn.close()
            return redirect(url_for('edit_funcionario',
                                error="Nenhum dado válido para atualização",
                                search_value=cpf))

        # Executar atualização
        query = f"UPDATE funcionarios SET {', '.join(updates)} WHERE id = ?"
        valores.append(funcionario_id)
        
        cursor.execute(query, valores)
        conn.commit()
        
        # Verificar se alguma linha foi afetada
        if cursor.rowcount == 0:
            conn.close()
            return redirect(url_for('edit_funcionario',
                                error="Nenhum dado foi atualizado",
                                search_value=cpf))
        
        conn.close()
        return redirect(url_for('edit_funcionario',
                            success="Dados atualizados com sucesso!",
                            search_value=cpf))
    
    except sqlite3.Error as e:
        app.logger.error(f"Erro SQL ao atualizar: {str(e)}")
        return redirect(url_for('edit_funcionario',
                            error=f"Erro no banco de dados: {str(e)}",
                            search_value=cpf))
    
    except Exception as e:
        app.logger.error(f"Erro inesperado: {str(e)}")
        return redirect(url_for('edit_funcionario',
                            error="Erro ao processar atualização",
                            search_value=cpf))

if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    os.makedirs('static/pdfs', exist_ok=True)
    app.run(host='127.0.0.1', port=8080, debug=True)