package com.aiops.notificationservice.service;

import com.aiops.notificationservice.dto.NotificationRequest;
import com.aiops.notificationservice.dto.NotificationResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    // Phase 1 has no real delivery channel (email/SMS/push) - "sending" a
    // notification just means logging it. This is still enough to prove the
    // end-to-end trace works across all 4 services.
    public NotificationResponse send(NotificationRequest request) {
        String notificationId = UUID.randomUUID().toString();
        log.info("Notification {} sent to customer {} for order {}: \"{}\"",
                notificationId, request.customerId(), request.orderId(), request.message());
        return new NotificationResponse(notificationId, "SENT");
    }
}
