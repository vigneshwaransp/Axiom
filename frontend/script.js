function sendMessage() {
    let input = document.getElementById("userInput");
    let chatBox = document.getElementById("chatBox");

    let userText = input.value;

    if (userText === "") return;

    // Show user message
    let userMsg = document.createElement("p");
    userMsg.textContent = "You: " + userText;
    chatBox.appendChild(userMsg);

    // Fake bot response
    let botMsg = document.createElement("p");
    botMsg.textContent = "Bot: " + "I got your message!";
    chatBox.appendChild(botMsg);

    // Clear input
    input.value = "";
}