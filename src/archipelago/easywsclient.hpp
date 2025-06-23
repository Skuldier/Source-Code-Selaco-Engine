// This is a simplified version of easywsclient for Archipelago integration
// Based on https://github.com/dhbaird/easywsclient

#ifndef EASYWSCLIENT_HPP
#define EASYWSCLIENT_HPP

#include <string>
#include <vector>
#include <functional>
#include <memory>

namespace easywsclient {

class WebSocket {
public:
    typedef std::function<void(const std::string& message)> MessageCallback;
    
    enum readyStateValues { CLOSING, CLOSED, CONNECTING, OPEN };
    
    // Factory method
    static WebSocket* from_url(const std::string& url, const std::string& origin = std::string());
    
    // Destructor
    virtual ~WebSocket() { }
    
    // Send a message
    virtual void send(const std::string& message) = 0;
    virtual void sendBinary(const std::string& message) = 0;
    virtual void sendBinary(const std::vector<uint8_t>& message) = 0;
    virtual void sendPing() = 0;
    
    // Close the connection
    virtual void close() = 0;
    
    // Get the current state
    virtual readyStateValues getReadyState() const = 0;
    
    // Process events - call this regularly
    virtual void poll(int timeout = 0) = 0;
    
    // Dispatch received messages to callback
    virtual void dispatch(MessageCallback message_callback) = 0;
};

} // namespace easywsclient

#endif // EASYWSCLIENT_HPP