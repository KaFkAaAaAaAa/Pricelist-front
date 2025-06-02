let skus = JSON.parse(document.getElementById("skus").textContent);

function isComments(commentColumn) {
  let out = false;
  commentColumn.forEach((field) => {
    if (field.textContent != "") out = true;
    return;
  });
  if (out) return true;
  return false;
}

function commentColumnHandler() {
  const commentColumn = document.querySelectorAll(".removable");
  test = isComments(commentColumn);
  if (test) {
    commentColumn.forEach((field) => {
      field.style.display = "";
    });
  } else {
    commentColumn.forEach((field) => {
      field.style.display = "none";
    });
  }
}

function checkSkuList() {
  const noItemsAlert = document.getElementById("alert-no-items");
  if (skus.length !== 0) {
    noItemsAlert.style.display = "";
  } else {
    noItemsAlert.style.display = "none";
  }
}

function getNextSku() {
  let prefix = "NA"; // Fixed prefix
  let maxNumber = 0;

  skus.forEach((sku) => {
    let match = sku.match(/^NA(\d\d)$/);
    if (match) {
      let num = parseInt(match[1], 10);
      if (num > maxNumber) {
        maxNumber = num;
      }
    }
  });
  let nextNumber = (maxNumber + 1).toString().padStart(2, "0"); // Ensure 2-digit format
  return `${prefix}${nextNumber}`;
}

const commentModal = document.getElementById("commentModal");
let skuComment = null;

if (commentModal) {
  commentModal.addEventListener("show.bs.modal", (event) => {
    const button = event.relatedTarget;
    skuComment = button.getAttribute("data-bs-sku");

    const inputComment = document.getElementById(
      `additionalInfo-${skuComment}`,
    );
  });
}

const modalSaveButton = document.getElementById("modalSaveButton");

modalSaveButton.addEventListener("click", (event) => {
  event.preventDefault();
  if (!skuComment) return;
  const inputComment = document.getElementById(`additionalInfo-${skuComment}`);
  const commentField = document.getElementById(`comment-${skuComment}`);
  const commentInput = document.getElementById("comment");
  if (inputComment) {
    inputComment.value = document.getElementById("comment").value;
    // TODO: add the link (optional) to present long comment
    inputComment.value = commentInput.value;
    if (commentField) commentField.textContent = inputComment.value;
    saveButton.style.display = "inline-block";
    commentColumnHandler();
  }
  const modal = bootstrap.Modal.getInstance(commentModal);
  modal.hide();
});

function deleteItem(event, sku) {
  event.stopPropagation();
  const deleteConfirm = JSON.parse(
    document.getElementById("delete-confirm").textContent,
  );
  if (confirm(`${deleteConfirm}?`)) {
    let itemElement = document.getElementById(sku);
    if (itemElement) {
      itemElement.remove();
    }
    skus = skus.filter((itemSku) => itemSku !== sku);
  }
  saveButton.style.display = "inline-block";
  checkSkuList();
  commentColumnHandler();
}

function calculateTotal(skuChanged) {
  let allTotalPrice = 0.0,
    allTotalAmount = 0.0;
  let amount =
    parseFloat(document.getElementById(`amount-${skuChanged}`).value) || 0;
  let pricePerKg =
    parseFloat(document.getElementById(`price-${skuChanged}`).value) || 0;
  document.getElementById(`totalPrice-${skuChanged}`).textContent = (
    amount * pricePerKg
  ).toFixed(2);

  skus.forEach((sku) => {
    let amount =
      parseFloat(document.getElementById(`amount-${sku}`).value) || 0;
    let pricePerKg =
      parseFloat(document.getElementById(`price-${sku}`).value) || 0;
    allTotalPrice += amount * pricePerKg;
    allTotalAmount += amount;
  });

  document.getElementById(`totalPrice`).textContent = allTotalPrice.toFixed(2);
  document.getElementById(`totalAmount`).textContent =
    allTotalAmount.toFixed(1);
}

function addItemToTransaction(sku, name, price) {
  const deleteLabel = JSON.parse(
    document.getElementById("delete-label").textContent,
  );
  const commentLabel = JSON.parse(
    document.getElementById("add-comment-label").textContent,
  );

  let newRow = document.createElement("tr");

  if (!sku) sku = getNextSku();
  skus.push(sku);

  let nameField, priceField;

  if (!name) {
    nameField = `
        <input name="name-${sku}" type="text" class="form-control text-start" required/>
    `;
  } else {
    nameField = `
        <input type="hidden" name="name-${sku}" value="${name}" required maxlength="255"/>
        <div class="ps-2 text-start">${name}</div>
    `;
  }
  if (!price) {
    priceField = `
        <div class="input-group">
        <input id="price-${sku}" name="price-${sku}" 
                type="number"
            value="${price}" min="0.01" step="0.01" required
            class="form-control ms-auto separator-input" style="max-width: 100px; margin: 0;"
            onchange="calculateTotal('${sku}')"><span class="input-group-text me-auto">€<span>
        </div>
    `;
  } else {
    priceField = `
        <input id="price-${sku}" name="price-${sku}" 
            type="hidden" value="${price}" min="0.01" step="0.01"
            onchange="calculateTotal('${sku}')" required />
        <div class="ps-2 text-start">${price} €</div>

    `;
  }
  checkSkuList();
  newRow.id = sku;
  newRow.innerHTML = `
        <input type="hidden" name="sku-${sku}" value="${sku}" />
        <td>${sku}</td>
        <td>${nameField}</td>
        <td>
            <div class="input-group text-center" style="margin: 0 auto;">
                <input id="amount-${sku}" name="amount-${sku}" type="number"
                       value="0.0" min="0.01" step="0.01"
                       class="form-control ms-auto separator-input" style="max-width: 100px;"
                       onchange="calculateTotal('${sku}')">
                <span class="input-group-text me-auto">kg<span>
            </div>
        </td>
        <td>${priceField}</td>
        <td class="text-end" style="white-space: nowrap;"><span class="separator" id="totalPrice-${sku}"></span> €</td>
        <input type="hidden" name="additionalInfo-${sku}" id="additionalInfo-${sku}" />
        <td class="removable" id="comment-${sku}"></td>
        <td>
            <div class="d-grid gap-1 w-100">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-target="#commentModal" data-bs-toggle="modal" data-bs-sku="${sku}">${commentLabel}</button>
                <button class="btn btn-outline-danger btn-sm" type="button" onclick="deleteItem(event, '${sku}');">${deleteLabel}</button>
            </div>
        </td>
    `;
  document.querySelector("table tbody").appendChild(newRow);
  calculateTotal(sku);
  saveButton.style.display = "inline-block";
  showSuccessAlert();
  commentColumnHandler();
}

function showSuccessAlert() {
  successAlert.style.display = "block";
  setTimeout(() => {
    successAlert.style.display = "none";
  }, 3000);
}

const successAlert = document.getElementById("successAlert");
function validateOffer() {
  if (skus.length === 0) {
    var emptyOfferModal = new bootstrap.Modal(
      document.getElementById("emptyOfferModal"),
    );
    emptyOfferModal.show();
    return false;
  }
  return true;
}

const form = document.getElementById("edit-form");
const inputs = form.querySelectorAll("input, textarea");
const saveButton = document.getElementById("saveButton");

inputs.forEach((input) => {
  input.addEventListener("input", () => {
    saveButton.style.display = "inline-block";
  });
});

form.addEventListener("submit", function (event) {
  const submitButton = document.activeElement;
  const saveChangesConfirm = JSON.parse(
    document.getElementById("save-changes-confirm").textContent,
  );
  if (submitButton && submitButton.type === "submit") {
    if (!confirm(`${saveChangesConfirm}?`)) {
      event.preventDefault();
    }
  }
});

document.addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    let searchModal = document.getElementById("searchModal");
    if (searchModal.classList.contains("show")) {
      event.preventDefault();
      document.getElementById("searchBtn").click();
    }
  }
});

document
  .getElementById("searchBtn")
  .addEventListener("click", function (event) {
    event.preventDefault();

    let query = document.getElementById("searchQuery").value.trim();

    if (!query) url = "/?f=json";
    else url = `/?search=${query}&f=json`;

    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        let resultsContainer = document.getElementById("searchResults");
        resultsContainer.innerHTML = "";

        if (data.items.length === 0) {
          resultsContainer.innerHTML = "<p>No items found.</p>";
          return;
        }

        let resultList = document.createElement("ul");
        resultList.classList.add("list-group");

        Object.entries(data.items).forEach(([category, categoryItems]) => {
          if (categoryItems.length === 0) {
            return;
          }
          let listItem = document.createElement("li");
          listItem.innerHTML = `<strong>${category}</strong>`;
          listItem.classList.add(
            "list-group-item",
            "text-left",
            "text-light",
            "fw-semibold",
            "text-uppercase",
            "align-middle",
          );
          listItem.style.backgroundColor = "#9E0F06";
          resultList.appendChild(listItem);
          categoryItems.forEach((item) => {
            let listItem = document.createElement("li");
            listItem.classList.add(
              "list-group-item",
              "d-flex",
              "justify-content-between",
              "align-items-center",
            );

            listItem.innerHTML = `
                        <span><strong>${item.sku}</strong> - ${item.name} (${item.price} €/kg)</span>
                        <button class="btn btn-sm btn-outline-success" data-bs-dismiss="modal" onclick="addItemToTransaction('${item.sku}', '${item.name}', ${item.price});">Add</button>
                    `;
            resultList.appendChild(listItem);
          });
        });

        resultsContainer.appendChild(resultList);
      })
      .catch((error) => console.error("Error fetching items: " + error));
  });

$(document).ready(function () {
  $("#select-client").select2({
    ajax: {
      url: "/clients/admin?format=json&query=query",
      dataType: "json",
      delay: 250,
      processResults: function (data) {
        return {
          results: data.map(function (item) {
            return {
              id: item.id,
              text: item.name,
            };
          }),
        };
      },
      cache: true,
    },
  });
});

const defaultValue = document.getElementById("defaultValue");
const defaultOption = { id: 1, text: defaultValue };
const option = new Option(defaultOption.text, defaultOption.id, true, true);
$("#select-client").append(option).trigger("change");

window.onload = () => {
  skus.forEach((sku) => calculateTotal(sku));
  checkSkuList();
  commentColumnHandler();
};
