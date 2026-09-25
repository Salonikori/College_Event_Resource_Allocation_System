document.addEventListener("DOMContentLoaded", () => {

    // =========================================================
    // COMMON HELPERS
    // =========================================================

    const isBlank = (value) => {
        return !value || value.trim() === "";
    };


    // =========================================================
    // CONFIRMATION MODAL
    // =========================================================
    const bindConfirmations = () => {
        const modal = document.getElementById("confirmModal");
        const messageEl = document.getElementById("confirmMessage");
        const proceed = document.getElementById("confirmProceed");
        const cancel = document.getElementById("confirmCancel");
        if (!modal) return;

        let pendingAction = null;
        const close = () => {
            modal.classList.add("hidden");
            modal.classList.remove("flex");
            pendingAction = null;
        };
        const open = (message, action) => {
            messageEl.textContent = message || "Are you sure you want to continue?";
            pendingAction = action;
            modal.classList.remove("hidden");
            modal.classList.add("flex");
        };
        proceed.addEventListener("click", () => {
            if (pendingAction) pendingAction();
            close();
        });
        cancel.addEventListener("click", close);
        modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
        document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });

        document.querySelectorAll("[data-confirm]").forEach((element) => {
            element.addEventListener("submit", (event) => {
                event.preventDefault();
                open(element.dataset.confirm, () => element.submit());
            });
        });
        document.querySelectorAll("[data-confirm-click]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                open(element.dataset.confirmClick, () => {
                    if (element.tagName === "BUTTON" && element.form) element.form.submit();
                    else if (element.dataset.confirmHref) window.location.href = element.dataset.confirmHref;
                });
            });
        });
    };

    // =========================================================
    // TOASTS
    // =========================================================
    const setupToasts = () => {
        document.querySelectorAll(".toast-item").forEach((toast) => {
            const close = () => {
                toast.style.opacity = "0";
                toast.style.transform = "translateX(12px)";
                toast.style.transition = "all .2s ease";
                setTimeout(() => toast.remove(), 220);
            };
            const btn = toast.querySelector(".toast-close");
            if (btn) btn.addEventListener("click", close);
            setTimeout(close, 4500);
        });
    };

    // =========================================================
    // DATE/TIME VALIDATION
    // =========================================================

    const validateDateRange = (
        startId,
        endId,
        messageId
    ) => {

        const start =
            document.getElementById(
                startId
            );

        const end =
            document.getElementById(
                endId
            );

        const message =
            messageId
                ? document.getElementById(
                    messageId
                )
                : null;


        if (!start || !end) {

            return () => true;

        }


        const validate = () => {

            if (
                !start.value
                ||
                !end.value
            ) {

                end.setCustomValidity("");

                if (message) {

                    message.textContent = "";

                    message.classList.add(
                        "hidden"
                    );

                }

                return true;

            }


            const invalid =
                end.value <= start.value;


            end.setCustomValidity(
                invalid
                    ? "End time must be after start time."
                    : ""
            );


            if (message) {

                message.textContent =
                    invalid
                        ? "End time must be after start time."
                        : "";

                message.classList.toggle(
                    "hidden",
                    !invalid
                );

            }


            return !invalid;

        };


        start.addEventListener(
            "change",
            validate
        );

        start.addEventListener(
            "input",
            validate
        );


        end.addEventListener(
            "change",
            validate
        );

        end.addEventListener(
            "input",
            validate
        );


        return validate;

    };


    // =========================================================
    // REQUIRED-FIELD BUTTON CONTROL
    // =========================================================

    const setupRequiredButton = (
        formId,
        buttonId,
        fieldIds
    ) => {

        const form =
            document.getElementById(
                formId
            );

        const button =
            document.getElementById(
                buttonId
            );


        if (!form || !button) {

            return;

        }


        const fields =
            fieldIds
                .map(
                    (id) =>
                        document.getElementById(id)
                )
                .filter(Boolean);


        const update = () => {

            const missing =
                fields.some(
                    (field) =>
                        isBlank(
                            field.value
                        )
                );


            button.disabled =
                missing;

        };


        fields.forEach(
            (field) => {

                field.addEventListener(
                    "input",
                    update
                );

                field.addEventListener(
                    "change",
                    update
                );

            }
        );


        update();

    };


    // =========================================================
    // AVAILABILITY FORM
    // =========================================================

    const setupAvailabilityForm = () => {

        const form =
            document.getElementById(
                "availabilityForm"
            );


        if (!form) {

            return;

        }


        const resource =
            document.getElementById(
                "resource_id"
            );

        const date =
            document.getElementById(
                "date"
            );

        const start =
            document.getElementById(
                "start_time"
            );

        const end =
            document.getElementById(
                "end_time"
            );

        const button =
            document.getElementById(
                "checkAvailabilityButton"
            );


        if (
            !resource
            ||
            !date
            ||
            !start
            ||
            !end
            ||
            !button
        ) {

            return;

        }


        const validateRange = () => {

            if (
                !start.value
                ||
                !end.value
            ) {

                end.setCustomValidity("");

                return true;

            }


            const invalid =
                end.value <= start.value;


            end.setCustomValidity(
                invalid
                    ? "End time must be after start time."
                    : ""
            );


            return !invalid;

        };


        const updateButton = () => {

            const missing =
                !resource.value
                ||
                !date.value
                ||
                !start.value
                ||
                !end.value;


            const invalid =
                !validateRange();


            button.disabled =
                missing || invalid;

        };


        [
            resource,
            date,
            start,
            end
        ].forEach(
            (field) => {

                field.addEventListener(
                    "input",
                    updateButton
                );

                field.addEventListener(
                    "change",
                    updateButton
                );

            }
        );


        form.addEventListener(
            "submit",
            (event) => {

                if (
                    !resource.value
                    ||
                    !date.value
                    ||
                    !start.value
                    ||
                    !end.value
                    ||
                    !validateRange()
                ) {

                    event.preventDefault();

                    form.reportValidity();

                }

            }
        );


        updateButton();

    };


    // =========================================================
    // MULTI-RESOURCE REQUEST FORM
    // =========================================================

    const setupMultiResourceForm = () => {

        const form =
            document.getElementById(
                "requestForm"
            );


        if (!form) {

            return;

        }


        const rowsContainer =
            document.getElementById(
                "resourceRows"
            );

        const addButton =
            document.getElementById(
                "addResourceBtn"
            );

        const error =
            document.getElementById(
                "resourceError"
            );


        if (
            !rowsContainer
            ||
            !addButton
        ) {

            return;

        }


        // =====================================================
        // SHOW ERROR
        // =====================================================

        const showError = (
            message
        ) => {

            if (!error) {
                return;
            }

            error.textContent =
                message;

            error.classList.remove(
                "hidden"
            );

        };


        const hideError = () => {

            if (!error) {
                return;
            }

            error.textContent = "";

            error.classList.add(
                "hidden"
            );

        };


        // =====================================================
        // FILTER SPECIFIC RESOURCES
        // =====================================================

        const filterSpecificResources = (
            row
        ) => {

            const typeSelect =
                row.querySelector(
                    ".resource-type"
                );

            const resourceSelect =
                row.querySelector(
                    ".specific-resource"
                );


            if (
                !typeSelect
                ||
                !resourceSelect
            ) {

                return;

            }


            const selectedType =
                typeSelect.value;


            resourceSelect
                .querySelectorAll(
                    "option[data-resource-type]"
                )
                .forEach(
                    (option) => {

                        const matches =
                            !selectedType
                            ||
                            option.dataset
                                .resourceType
                                === selectedType;


                        option.hidden =
                            !matches;


                        if (
                            !matches
                            &&
                            option.selected
                        ) {

                            resourceSelect.value =
                                "";

                        }

                    }
                );

        };


        // =====================================================
        // DUPLICATE TYPES
        // =====================================================

        const validateDuplicateTypes = () => {

            const seen =
                new Set();


            let duplicate =
                false;


            rowsContainer
                .querySelectorAll(
                    ".resource-type"
                )
                .forEach(
                    (select) => {

                        if (!select.value) {

                            return;

                        }


                        if (
                            seen.has(
                                select.value
                            )
                        ) {

                            duplicate =
                                true;

                        }


                        seen.add(
                            select.value
                        );

                    }
                );


            if (duplicate) {

                showError(
                    "Each resource type can be added only once. " +
                    "Increase its quantity instead."
                );


                return false;

            }


            hideError();


            return true;

        };


        // =====================================================
        // UPDATE REMOVE BUTTONS
        // =====================================================

        const updateRemoveButtons = () => {

            const rows =
                rowsContainer.querySelectorAll(
                    ".resource-row"
                );


            rows.forEach(
                (row) => {

                    const button =
                        row.querySelector(
                            ".remove-resource-btn"
                        );


                    if (!button) {

                        return;

                    }


                    const onlyRow =
                        rows.length === 1;


                    button.disabled =
                        onlyRow;


                    button.classList.toggle(
                        "opacity-50",
                        onlyRow
                    );


                    button.classList.toggle(
                        "cursor-not-allowed",
                        onlyRow
                    );

                }
            );

        };


        // =====================================================
        // BIND RESOURCE ROW
        // =====================================================

        const bindRow = (
            row
        ) => {

            const typeSelect =
                row.querySelector(
                    ".resource-type"
                );

            const removeButton =
                row.querySelector(
                    ".remove-resource-btn"
                );


            if (typeSelect) {

                typeSelect.addEventListener(
                    "change",
                    () => {

                        filterSpecificResources(
                            row
                        );

                        validateDuplicateTypes();

                    }
                );

            }


            if (removeButton) {

                removeButton.addEventListener(
                    "click",
                    () => {

                        const rows =
                            rowsContainer.querySelectorAll(
                                ".resource-row"
                            );


                        if (
                            rows.length <= 1
                        ) {

                            return;

                        }


                        row.remove();


                        updateRemoveButtons();

                        validateDuplicateTypes();

                    }
                );

            }


            filterSpecificResources(
                row
            );

        };


        // =====================================================
        // INITIAL ROWS
        // =====================================================

        rowsContainer
            .querySelectorAll(
                ".resource-row"
            )
            .forEach(
                bindRow
            );


        updateRemoveButtons();


        // =====================================================
        // ADD ROW
        // =====================================================

        addButton.addEventListener(
            "click",
            () => {

                const firstRow =
                    rowsContainer.querySelector(
                        ".resource-row"
                    );


                if (!firstRow) {

                    return;

                }


                const newRow =
                    firstRow.cloneNode(
                        true
                    );


                const typeSelect =
                    newRow.querySelector(
                        ".resource-type"
                    );


                const quantity =
                    newRow.querySelector(
                        "input[name='quantity']"
                    );


                const specific =
                    newRow.querySelector(
                        ".specific-resource"
                    );


                if (typeSelect) {

                    typeSelect.value =
                        "";

                }


                if (quantity) {

                    quantity.value =
                        "1";

                }


                if (specific) {

                    specific.value =
                        "";

                    specific
                        .querySelectorAll(
                            "option"
                        )
                        .forEach(
                            (option) => {

                                option.hidden =
                                    false;

                            }
                        );

                }


                rowsContainer.appendChild(
                    newRow
                );


                bindRow(
                    newRow
                );


                updateRemoveButtons();

            }
        );


        // =====================================================
        // SUBMIT VALIDATION
        // =====================================================

        form.addEventListener(
            "submit",
            (event) => {

                hideError();


                const eventId =
                    form.querySelector(
                        "#event_id"
                    );


                const start =
                    form.querySelector(
                        "#requested_start"
                    );


                const end =
                    form.querySelector(
                        "#requested_end"
                    );


                // ---------------------------------------------
                // Required event
                // ---------------------------------------------

                if (
                    eventId
                    &&
                    !eventId.value
                ) {

                    event.preventDefault();

                    showError(
                        "Please select an event."
                    );

                    eventId.focus();

                    return;

                }


                // ---------------------------------------------
                // Date/time
                // ---------------------------------------------

                if (
                    start
                    &&
                    end
                    &&
                    start.value
                    &&
                    end.value
                    &&
                    end.value <= start.value
                ) {

                    event.preventDefault();

                    end.setCustomValidity(
                        "End time must be after start time."
                    );

                    end.reportValidity();

                    return;

                }


                // ---------------------------------------------
                // Resource rows
                // ---------------------------------------------

                const rows =
                    rowsContainer.querySelectorAll(
                        ".resource-row"
                    );


                if (!rows.length) {

                    event.preventDefault();

                    showError(
                        "Please add at least one resource."
                    );

                    return;

                }


                // ---------------------------------------------
                // Validate every row
                // ---------------------------------------------

                for (
                    const row of rows
                ) {

                    const type =
                        row.querySelector(
                            ".resource-type"
                        );

                    const quantity =
                        row.querySelector(
                            "input[name='quantity']"
                        );


                    if (
                        !type
                        ||
                        !type.value
                    ) {

                        event.preventDefault();

                        showError(
                            "Please select a resource type for every row."
                        );

                        if (type) {

                            type.focus();

                        }

                        return;

                    }


                    const quantityValue =
                        Number(
                            quantity.value
                        );


                    if (
                        !Number.isInteger(
                            quantityValue
                        )
                        ||
                        quantityValue <= 0
                    ) {

                        event.preventDefault();

                        showError(
                            "Every resource quantity must be a positive whole number."
                        );

                        quantity.focus();

                        return;

                    }

                }


                // ---------------------------------------------
                // Duplicate resource types
                // ---------------------------------------------

                if (
                    !validateDuplicateTypes()
                ) {

                    event.preventDefault();

                }

            }
        );

    };


    // =========================================================
    // INLINE RESOURCE CONFLICT CHECK
    // =========================================================
    const setupInlineConflictCheck = () => {
        const form = document.getElementById("requestForm");
        if (!form) return;
        const start = document.getElementById("requested_start");
        const end = document.getElementById("requested_end");
        const container = document.getElementById("inlineConflictWarning");
        if (!start || !end || !container) return;

        let timer;
        const check = async () => {
            container.innerHTML = "";
            container.classList.add("hidden");
            if (!start.value || !end.value || end.value <= start.value) return;
            const rows = [...form.querySelectorAll(".resource-row")];
            if (!rows.length) return;
            clearTimeout(timer);
            timer = setTimeout(async () => {
                const warnings = [];
                for (const row of rows) {
                    const specific = row.querySelector(".specific-resource");
                    const type = row.querySelector(".resource-type");
                    const quantity = row.querySelector("input[name='quantity']");
                    if (!type?.value) continue;
                    try {
                        const params = new URLSearchParams({
                            start: start.value,
                            end: end.value,
                            resource_type: type.value,
                            quantity: quantity?.value || "1"
                        });
                        if (specific?.value) params.set("resource_id", specific.value);
                        const response = await fetch(`/requests/api/conflicts?${params}`, { headers: {"Accept":"application/json"} });
                        if (!response.ok) continue;
                        const data = await response.json();
                        if (!data.available) {
                            if (specific?.value && data.conflicts?.length) {
                                warnings.push(`<div class="font-medium">⚠️ ${data.resource_name} is booked</div><div class="text-xs mt-1">${data.conflicts.map(c => `${c.start} – ${c.end}`).join("<br>")}</div>`);
                            } else {
                                warnings.push(`<div class="font-medium">⚠️ Not enough ${type.value.replaceAll("_"," ").toLowerCase()} resources are free</div><div class="text-xs mt-1">${data.available_count || 0} available for ${data.required}</div>`);
                            }
                        }
                    } catch (_) {}
                }
                if (warnings.length) {
                    container.innerHTML = warnings.join('<div class="border-t border-amber-200 my-2"></div>');
                    container.classList.remove("hidden");
                }
            }, 250);
        };
        [start, end].forEach(el => ["change","input"].forEach(evt => el.addEventListener(evt, check)));
        form.addEventListener("change", e => {
            if (e.target.classList.contains("specific-resource")) check();
        });
    };

    // =========================================================
    // DAY TIMELINE
    // =========================================================
    const setupTimeline = () => {
        const timeline = document.getElementById("resourceTimeline");
        const dateInput = document.getElementById("timelineDate");
        if (!timeline || !dateInput) return;
        const bookings = [...timeline.querySelectorAll(".timeline-booking")];
        const render = () => {
            const date = dateInput.value;
            bookings.forEach(card => {
                const start = new Date(card.dataset.start);
                const end = new Date(card.dataset.end);
                const sameDay = date && start.toISOString().slice(0,10) === date;
                card.style.display = sameDay ? "block" : "none";
                if (!sameDay) return;
                const startMin = start.getHours()*60 + start.getMinutes();
                const endMin = Math.max(startMin + 30, end.getHours()*60 + end.getMinutes());
                card.style.left = `${Math.max(0, startMin / 1440 * 100)}%`;
                card.style.width = `${Math.max(3, (endMin-startMin)/1440*100)}%`;
            });
            timeline.querySelectorAll(".timeline-empty").forEach(x => x.remove());
            if (date && bookings.every(b => b.style.display === "none")) {
                const empty = document.createElement("div");
                empty.className = "timeline-empty absolute inset-0 flex items-center justify-center text-sm text-gray-500";
                empty.textContent = "No bookings on this day";
                timeline.appendChild(empty);
            }
        };
        dateInput.addEventListener("change", render);
        render();
    };

    // =========================================================
    // INITIALIZE EVERYTHING
    // =========================================================

    bindConfirmations();
    setupToasts();


    validateDateRange(
        "requested_start",
        "requested_end",
        "requestDateError"
    );


    validateDateRange(
        "start_dt",
        "end_dt",
        "eventDateError"
    );


    validateDateRange(
        "start",
        "end",
        "availabilityDateError"
    );


    setupAvailabilityForm();

    setupMultiResourceForm();
    setupInlineConflictCheck();
    setupTimeline();

});