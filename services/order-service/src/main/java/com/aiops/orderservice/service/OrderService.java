package com.aiops.orderservice.service;

import com.aiops.orderservice.client.InventoryClient;
import com.aiops.orderservice.client.PaymentClient;
import com.aiops.orderservice.config.RuntimeConfig;
import com.aiops.orderservice.dto.*;
import com.aiops.orderservice.filter.TraceIdFilter;
import com.aiops.orderservice.model.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    // Phase 1 has no database - orders live in memory for the lifetime of the process.
    private final Map<String, Order> orders = new ConcurrentHashMap<>();

    private final PaymentClient paymentClient;
    private final InventoryClient inventoryClient;
    private final RuntimeConfig runtimeConfig;

    public OrderService(PaymentClient paymentClient, InventoryClient inventoryClient, RuntimeConfig runtimeConfig) {
        this.paymentClient = paymentClient;
        this.inventoryClient = inventoryClient;
        this.runtimeConfig = runtimeConfig;
    }

    public OrderResponse placeOrder(OrderRequest request) {
        String traceId = MDC.get(TraceIdFilter.MDC_TRACE_ID_KEY);

        // Phase 6 gateway check: rejects the exact failure mode
        // (amount <= 0 sailing all the way to payment-service before being
        // declined) that auto-remediation flips this flag on for. Runs
        // before an Order record even exists - a true gateway rejection,
        // not a business-logic failure recorded against a real order.
        if (runtimeConfig.isRejectZeroAmount() && request.amount() <= 0) {
            log.warn("Order rejected at gateway - invalid amount (amount={}, customer={})",
                    request.amount(), request.customerId());
            return new OrderResponse(null, traceId, "REJECTED_AT_GATEWAY", "Amount must be positive");
        }

        String orderId = UUID.randomUUID().toString();

        Order order = new Order(orderId, traceId, request.productId(), request.quantity(),
                request.amount(), request.customerId());
        orders.put(orderId, order);

        log.info("Order {} created for customer {} (product={}, qty={}, amount={})",
                orderId, request.customerId(), request.productId(), request.quantity(), request.amount());

        // Step 1: charge the customer via payment-service.
        PaymentResponse paymentResponse;
        try {
            paymentResponse = paymentClient.charge(new PaymentRequest(orderId, request.customerId(), request.amount()));
        } catch (RestClientException ex) {
            order.setStatus("FAILED");
            log.error("Order {} failed - payment-service unreachable or errored: {}", orderId, ex.getMessage());
            return new OrderResponse(orderId, traceId, "FAILED", "Payment could not be processed");
        }

        if (!"SUCCESS".equals(paymentResponse.status())) {
            order.setStatus("FAILED");
            log.warn("Order {} failed - payment declined", orderId);
            return new OrderResponse(orderId, traceId, "FAILED", "Payment declined");
        }

        order.setStatus("PAYMENT_CONFIRMED");
        log.info("Order {} payment confirmed (paymentId={})", orderId, paymentResponse.paymentId());

        // Step 2: reserve stock via inventory-service.
        InventoryResponse inventoryResponse;
        try {
            inventoryResponse = inventoryClient.reserve(new InventoryRequest(orderId, request.productId(), request.quantity()));
        } catch (RestClientException ex) {
            order.setStatus("INVENTORY_FAILED");
            log.error("Order {} paid but inventory reservation errored: {}", orderId, ex.getMessage());
            return new OrderResponse(orderId, traceId, "INVENTORY_FAILED", "Payment succeeded but inventory service is unreachable");
        }

        if (!"RESERVED".equals(inventoryResponse.status())) {
            order.setStatus("INVENTORY_FAILED");
            log.warn("Order {} paid but out of stock", orderId);
            return new OrderResponse(orderId, traceId, "INVENTORY_FAILED", "Payment succeeded but item is out of stock");
        }

        order.setStatus("COMPLETED");
        log.info("Order {} completed successfully", orderId);
        return new OrderResponse(orderId, traceId, "COMPLETED", "Order placed successfully");
    }

    public Order getOrder(String orderId) {
        return orders.get(orderId);
    }
}
