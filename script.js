function enviarCodigo() {
    const email = document.getElementById("email").value;
    if (email) {
      const codigo = "123456"; // Código fixo de exemplo
      localStorage.setItem("codigo", codigo);
      localStorage.setItem("email", email);
      alert("Código enviado para " + email + ": " + codigo);
      window.location.href = "codepassword.html";
    } else {
      alert("Digite um email válido.");
    }
  }
  
  function verificarCodigo() {
    const codDigitado = document.getElementById("codigo").value;
    const codigoSalvo = localStorage.getItem("codigo");
  
    if (codDigitado === codigoSalvo) {
      alert("Código correto!");
      window.location.href = "newpassword.html";
    } else {
      alert("Código incorreto.");
    }
  }
  
  function salvarNovaSenha() {
    const senha = document.getElementById("senha").value;
    const confirmar = document.getElementById("confirmar").value;
  
    if (senha === confirmar && senha.length > 0) {
      alert("Senha redefinida com sucesso!");
      window.location.href = "Login.html";
    } else {
      alert("As senhas não coincidem ou estão vazias.");
    }
  }
  
  function login() {
    const email = document.getElementById("loginEmail").value;
    const senha = document.getElementById("loginSenha").value;
  
    if (email && senha) {
      alert("Login bem-sucedido!");
      window.location.href = "index.html";
    } else {
      alert("Preencha os campos.");
    }
  }
  