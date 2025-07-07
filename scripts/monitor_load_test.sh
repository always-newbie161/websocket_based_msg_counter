#!/bin/bash

# High-concurrency monitoring script
# Monitors system resources during load testing

DURATION=${1:-300}  # Default 5 minutes
TEST_TYPE=${2:-"5k"}  # Default test type

echo "🔍 Starting high-concurrency monitoring for ${DURATION} seconds..."
echo "📊 Test type: ${TEST_TYPE}"
echo "⏰ Started at: $(date)"
echo ""

# Create monitoring log file
LOG_FILE="reports/monitoring_${TEST_TYPE}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p reports

# Function to log system stats
log_stats() {
    echo "=== $(date) ===" >> $LOG_FILE
    
    # CPU and Memory
    echo "CPU & Memory:" >> $LOG_FILE
    top -l 1 -n 0 | grep "CPU usage\|PhysMem" >> $LOG_FILE
    
    # Docker container stats
    echo "Docker Stats:" >> $LOG_FILE
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" >> $LOG_FILE
    
    # Network connections
    echo "Network Connections:" >> $LOG_FILE
    netstat -an | grep ":8080\|:8001" | wc -l | sed 's/^/  Active connections: /' >> $LOG_FILE
    netstat -an | grep ":8080.*ESTABLISHED\|:8001.*ESTABLISHED" | wc -l | sed 's/^/  Established connections: /' >> $LOG_FILE
    
    # WebSocket-specific metrics (if available)
    echo "WebSocket Metrics:" >> $LOG_FILE
    curl -s http://localhost:8080/metrics/ | grep websocket_ >> $LOG_FILE 2>/dev/null || echo "  Metrics not available" >> $LOG_FILE
    
    echo "" >> $LOG_FILE
}

# Function to display real-time stats
display_stats() {
    clear
    echo "🔍 High-Concurrency Load Test Monitor"
    echo "======================================"
    echo "Test Type: ${TEST_TYPE}"
    echo "Duration: ${DURATION}s"
    echo "Started: $(date)"
    echo ""
    
    # Docker stats
    echo "📊 Container Resources:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    echo ""
    
    # Network connections
    echo "🌐 Network Connections:"
    TOTAL_CONN=$(netstat -an | grep ":8080\|:8001" | wc -l | tr -d ' ')
    ESTABLISHED_CONN=$(netstat -an | grep ":8080.*ESTABLISHED\|:8001.*ESTABLISHED" | wc -l | tr -d ' ')
    echo "  Total connections: ${TOTAL_CONN}"
    echo "  Established connections: ${ESTABLISHED_CONN}"
    echo ""
    
    # WebSocket metrics
    echo "📈 WebSocket Metrics:"
    curl -s http://localhost:8080/metrics/ | grep websocket_ | head -5 || echo "  Metrics not available"
    echo ""
    
    # System resources
    echo "💻 System Resources:"
    top -l 1 -n 0 | grep "CPU usage\|PhysMem"
    echo ""
    
    echo "📝 Logging to: ${LOG_FILE}"
    echo "⏰ Time remaining: $((DURATION - ELAPSED))s"
}

# Start monitoring
START_TIME=$(date +%s)
ELAPSED=0

echo "Starting monitoring loop..."
while [ $ELAPSED -lt $DURATION ]; do
    log_stats
    display_stats
    
    sleep 5
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
done

echo ""
echo "✅ Monitoring completed!"
echo "📊 Results logged to: ${LOG_FILE}"
echo "⏰ Finished at: $(date)"

# Generate summary
echo ""
echo "📋 Summary:"
echo "==========="
echo "Peak connections:" $(grep "Established connections:" $LOG_FILE | awk '{print $3}' | sort -n | tail -1)
echo "Average CPU usage:" $(grep "CPU usage:" $LOG_FILE | awk '{print $3}' | tr -d '%' | awk '{sum+=$1; count++} END {printf "%.1f%%\n", sum/count}')
echo "Log file: ${LOG_FILE}"
