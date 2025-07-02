import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaBars, FaPaperPlane, FaSpinner, FaThumbsUp, FaThumbsDown, FaRedo } from 'react-icons/fa';
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
  font-size: 1.5rem;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }
`;

const ChatContainer = styled.div`
  width: 350px;
  height: 100%;
  background-color: #fff;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  z-index: 10;
  overflow: hidden;
  transition: all 0.3s ease;
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
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
  transition: transform 0.2s ease;

  &:hover {
    transform: scale(1.1);
  }
`;

const MessagesContainer = styled.div`
  flex-grow: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #f8f9fa;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
  }

  &::-webkit-scrollbar-thumb {
    background: #01a3a4;
    border-radius: 3px;
  }
`;

const MessageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  max-width: 85%;
  margin-bottom: 8px;
  
  ${props => props.isUser ? `
    align-self: flex-end;
  ` : `
    align-self: flex-start;
  `}
`;

const Message = styled.div`
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
  line-height: 1.4;
  
  ${props => props.isUser ? `
    background-color: #01a3a4;
    color: white;
    border-bottom-right-radius: 5px;
  ` : `
    background-color: white;
    color: #333;
    border-bottom-left-radius: 5px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  `}
`;

const MessageTime = styled.span`
  font-size: 0.7rem;
  color: #666;
  margin-top: 4px;
  align-self: ${props => props.isUser ? 'flex-end' : 'flex-start'};
`;

const ChatInputContainer = styled.div`
  padding: 15px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  background-color: white;
`;

const ChatInput = styled.input`
  flex-grow: 1;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;

  &:focus {
    border-color: #01a3a4;
    box-shadow: 0 0 0 2px rgba(1, 163, 164, 0.1);
  }
`;

const SendButton = styled.button`
  background-color: #01a3a4;
  color: white;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background-color: #018f90;
    transform: scale(1.05);
  }

  &:disabled {
    background-color: #ccc;
    cursor: not-allowed;
    transform: none;
  }
`;

const LoadingSpinner = styled(FaSpinner)`
  animation: spin 1s linear infinite;
  margin-right: 8px;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ChatPanel = ({ onLocationSelect, onShowLocations }) => {
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      text: "Hello! I am your assistant for road defects, sensors, detection events, CRM cases, and road segments. Ask me anything about defects, sensors, events, cases, or roads!", 
      isUser: false,
      timestamp: new Date()
    },
  ]);
  const [newMessage, setNewMessage] = useState("");
  const [minimized, setMinimized] = useState(false);
  const [lastLocations, setLastLocations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const [feedback, setFeedback] = useState({});
  const [regeneratePrompt, setRegeneratePrompt] = useState(null);
  const [regenerating, setRegenerating] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (newMessage.trim() === "" || isLoading) return;

    const userMessage = {
      id: messages.length + 1,
      text: newMessage,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setNewMessage("");
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: newMessage })
      });
      const data = await res.json();
      
      if (data.locations && Array.isArray(data.locations) && data.locations.length > 0) {
        setLastLocations(data.locations);
        onShowLocations(data.locations);
      }
      if (data.location) {
        onLocationSelect(data.location);
      }

      const botResponse = {
        id: messages.length + 2,
        text: data.response,
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      setMessages(prev => [
        ...prev,
        { 
          id: messages.length + 2, 
          text: "Sorry, I couldn't reach the bot. Please try again later.", 
          isUser: false,
          timestamp: new Date()
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      const lastMsg = messages[messages.length-1];
      if (lastMsg.isUser && /show (me )?these locations/i.test(lastMsg.text) && lastLocations.length > 0) {
        onShowLocations(lastLocations);
      }
    }
  }, [messages, lastLocations, onShowLocations]);

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const findUserMessageForBot = (botMsgIdx) => {
    for (let i = botMsgIdx - 1; i >= 0; i--) {
      if (messages[i].isUser) return messages[i];
    }
    return null;
  };

  const handleRegenerate = async (botMsgIdx) => {
    const botMsg = messages[botMsgIdx];
    const userMsg = findUserMessageForBot(botMsgIdx);
    if (!userMsg) return;
    setRegenerating(true);
    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.text })
      });
      const data = await res.json();
      if (data.locations && Array.isArray(data.locations) && data.locations.length > 0) {
        setLastLocations(data.locations);
        onShowLocations(data.locations);
      }
      if (data.location) {
        onLocationSelect(data.location);
      }
      setMessages(prev => prev.map((msg, idx) =>
        idx === botMsgIdx ? { ...msg, text: data.response, timestamp: new Date() } : msg
      ));
      setFeedback(prev => ({ ...prev, [messages[botMsgIdx].id]: undefined }));
      setRegeneratePrompt(null);
    } catch (error) {
      setMessages(prev => prev.map((msg, idx) =>
        idx === botMsgIdx ? { ...msg, text: "Sorry, I couldn't regenerate the response. Please try again later.", timestamp: new Date() } : msg
      ));
    } finally {
      setRegenerating(false);
    }
  };

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
            Chat Assistant
          </ChatHeaderBar>
          <MessagesContainer>
            {messages.map((message, idx) => (
              <MessageWrapper key={message.id} isUser={message.isUser}>
                <Message isUser={message.isUser}>
                  {message.isUser ? message.text : parse(message.text)}
                </Message>
                <MessageTime isUser={message.isUser}>
                  {formatTime(message.timestamp)}
                </MessageTime>
                {!message.isUser && idx !== 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <button
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: feedback[message.id] === 'like' ? '#01a3a4' : '#888', fontSize: 18 }}
                      aria-label="Like response"
                      disabled={!!feedback[message.id]}
                      onClick={() => setFeedback(prev => ({ ...prev, [message.id]: 'like' }))}
                    >
                      <FaThumbsUp />
                    </button>
                    <button
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: feedback[message.id] === 'dislike' ? '#e74c3c' : '#888', fontSize: 18 }}
                      aria-label="Dislike response"
                      disabled={!!feedback[message.id]}
                      onClick={() => {
                        setFeedback(prev => ({ ...prev, [message.id]: 'dislike' }));
                        setRegeneratePrompt(message.id);
                      }}
                    >
                      <FaThumbsDown />
                    </button>
                    {feedback[message.id] === 'like' && <span style={{ color: '#01a3a4', fontSize: 13 }}>Thank you for your feedback!</span>}
                  </div>
                )}
                {!message.isUser && feedback[message.id] === 'dislike' && regeneratePrompt === message.id && (
                  <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 13 }}>Do you want to regenerate this response?</span>
                    <button
                      style={{ background: '#01a3a4', color: 'white', border: 'none', borderRadius: 16, padding: '4px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 14 }}
                      onClick={() => handleRegenerate(idx)}
                      disabled={regenerating}
                    >
                      {regenerating ? <LoadingSpinner style={{ margin: 0 }} /> : <FaRedo />} Regenerate
                    </button>
                    <button
                      style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 14 }}
                      onClick={() => setRegeneratePrompt(null)}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </MessageWrapper>
            ))}
            <div ref={messagesEndRef} />
          </MessagesContainer>
          <ChatInputContainer>
            <ChatInput 
              type="text" 
              placeholder="Type your message here..." 
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
            <SendButton 
              onClick={handleSendMessage}
              disabled={isLoading || !newMessage.trim()}
              title="Send message"
            >
              {isLoading ? <LoadingSpinner /> : <FaPaperPlane />}
            </SendButton>
          </ChatInputContainer>
        </ChatContainer>
      )}
    </>
  );
};

export default ChatPanel; 