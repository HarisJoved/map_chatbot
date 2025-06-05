import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { FaBars } from 'react-icons/fa';
import parse from 'html-react-parser';

const FloatingHamburger = styled.button`
  position: fixed;
  left: 10px;
  top: 10px;
  transform: none;
  background: #01a3a4;
  color: white;
  border: none;
  border-radius: 50%;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  cursor: pointer;
`;

const ChatContainer = styled.div`
  width: 300px;
  height: 100%;
  background-color: #fff;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 10;
  overflow: hidden;
`;

const ChatHeaderBar = styled.div`
  display: flex;
  align-items: center;
  padding: 15px;
  background-color: #01a3a4;
  color: white;
  font-weight: bold;
  font-size: 1.2rem;
  border-radius: 0 0 5px 0;
`;

const HamburgerButton = styled.button`
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  margin-right: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
`;

const MessagesContainer = styled.div`
  flex-grow: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const Message = styled.div`
  max-width: 80%;
  padding: 10px 15px;
  border-radius: 18px;
  margin-bottom: 5px;
  word-wrap: break-word;
  
  ${props => props.isUser ? `
    align-self: flex-end;
    background-color: #01a3a4;
    color: white;
    border-bottom-right-radius: 5px;
  ` : `
    align-self: flex-start;
    background-color: #f1f1f1;
    color: #333;
    border-bottom-left-radius: 5px;
  `}
`;

const ChatInputContainer = styled.div`
  padding: 15px;
  border-top: 1px solid #eee;
  display: flex;
`;

const ChatInput = styled.input`
  flex-grow: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
  &:focus {
    border-color: #01a3a4;
  }
`;

const SendButton = styled.button`
  background-color: #01a3a4;
  color: white;
  border: none;
  border-radius: 20px;
  padding: 10px 15px;
  margin-left: 10px;
  cursor: pointer;
  font-weight: bold;
  &:hover {
    background-color: #018f90;
  }
`;

const ChatPanel = ({ onLocationSelect, onShowLocations }) => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I am your assistant for road defects, sensors, detection events, CRM cases, and road segments. Ask me anything about defects, sensors, events, cases, or roads!", isUser: false },
  ]);
  const [newMessage, setNewMessage] = useState("");
  const [minimized, setMinimized] = useState(false);
  const [lastLocations, setLastLocations] = useState([]);

  const handleSendMessage = async () => {
    if (newMessage.trim() === "") return;

    const userMessage = {
      id: messages.length + 1,
      text: newMessage,
      isUser: true
    };

    setMessages([...messages, userMessage]);
    setNewMessage("");

    // Call FastAPI backend
    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: newMessage })
      });
      const data = await res.json();
      
      // If response contains locations array, store and show them
      if (data.locations && Array.isArray(data.locations) && data.locations.length > 0) {
        setLastLocations(data.locations);
        onShowLocations(data.locations);
      }
      // If response contains a single location
      if (data.location) {
        onLocationSelect(data.location);
      }

      const botResponse = {
        id: messages.length + 2,
        text: data.response,
        isUser: false
      };
      setMessages(prevMessages => [...prevMessages, botResponse]);
    } catch (error) {
      setMessages(prevMessages => [
        ...prevMessages,
        { id: messages.length + 2, text: "Sorry, I couldn't reach the bot.", isUser: false }
      ]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  // If user asks to show these locations, trigger onShowLocations
  useEffect(() => {
    if (messages.length > 0) {
      const lastMsg = messages[messages.length-1];
      if (lastMsg.isUser && /show (me )?these locations/i.test(lastMsg.text) && lastLocations.length > 0) {
        onShowLocations(lastLocations);
      }
    }
    // eslint-disable-next-line
  }, [messages]);

  return (
    <>
      {minimized ? (
        <FloatingHamburger onClick={() => setMinimized(false)} aria-label="Expand chat">
          <FaBars />
        </FloatingHamburger>
      ) : (
        <ChatContainer>
          <ChatHeaderBar>
            <HamburgerButton onClick={() => setMinimized(true)} aria-label="Minimize chat">
              <FaBars />
            </HamburgerButton>
            Chat
          </ChatHeaderBar>
          <MessagesContainer>
            {messages.map(message => (
              <Message key={message.id} isUser={message.isUser}>
                {message.isUser ? message.text : parse(message.text)}
              </Message>
            ))}
          </MessagesContainer>
          <ChatInputContainer>
            <ChatInput 
              type="text" 
              placeholder="Type your message here..." 
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <SendButton onClick={handleSendMessage}>
              Send
            </SendButton>
          </ChatInputContainer>
        </ChatContainer>
      )}
    </>
  );
};

export default ChatPanel; 