package com.aiops.paymentservice.service;

import com.aiops.paymentservice.client.NotificationClient;
import com.aiops.paymentservice.dto.NotificationRequest;
import com.aiops.paymentservice.dto.PaymentRequest;
import com.aiops.paymentservice.dto.PaymentResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

import java.util.UUID;

@Service
public class PaymentService {

    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    private final NotificationClient notificationClient;

    public PaymentService(NotificationClient notificationClient) {
        this.notificationClient = notificationClient;
    }

    public PaymentResponse charge(PaymentRequest request) {
        String paymentId = UUID.randomUUID().toString();
        log.info("Processing payment {} for order {} (amount={})", paymentId, request.orderId(), request.amount());

        // No real payment gateway in Phase 1 - a positive amount always succeeds.
        // This still gives us a real failure path (amount <= 0) to generate error logs with.
        String status = request.amount() > 0 ? "SUCCESS" : "FAILED";

        if ("FAILED".equals(status)) {
            log.warn("Payment {} declined for order {} - invalid amount {}", paymentId, request.orderId(), request.amount());
            return new PaymentResponse(paymentId, request.orderId(), status);
        }

        log.info("Payment {} succeeded for order {}", paymentId, request.orderId());

        // Notify the customer. This is a best-effort call: if notification-service
        // is down, the payment itself must NOT be rolled back - that would be a
        // realistic partial-failure scenario for the anomaly detector to catch later.
        try {
            notificationClient.send(new NotificationRequest(
                    request.orderId(), request.customerId(),
                    "Payment of " + request.amount() + " received for order " + request.orderId()));
        } catch (RestClientException ex) {
            log.error("Payment {} succeeded but notification failed for order {}: {}",
                    paymentId, request.orderId(), ex.getMessage());
        }

        return new PaymentResponse(paymentId, request.orderId(), status);
    }
}
