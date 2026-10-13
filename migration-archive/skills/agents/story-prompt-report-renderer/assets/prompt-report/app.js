(() => {
  "use strict";

  const TYPE_ORDER = ["G", "C", "W", "S", "P", "V", "E", "L", "F", "A"];
  const CATEGORY_ORDER = ["C", "W:costume", "W:hair", "W:makeup", "S", "P", "V", "E", "L", "F", "A"];
  const CATEGORY_LABELS = {
    C: "角色本体",
    "W:costume": "服装",
    "W:hair": "发型与胡须",
    "W:makeup": "妆容与彩绘",
    S: "场景本体",
    P: "道具",
    V: "载具与生物",
    E: "环境",
    L: "灯光与色彩",
    F: "特效",
    A: "声音",
  };
  const TYPE_LABELS = {
    G: "全局视觉圣经",
    C: "角色",
    W: "服装妆发",
    S: "场景置景",
    P: "道具",
    V: "载具与生物",
    E: "环境状态",
    L: "灯光色彩",
    F: "特效",
    A: "声音",
  };
  const ENTITY_LABELS = { character: "角色", scene: "场景" };
  const QUALITY_LABELS = { pass: "通过", warning: "注意", pending: "待确认" };
  const SOURCE_LABELS = {
    user: "用户明确",
    source_text: "原文明确",
    style_bible: "视觉圣经",
    inference: "合理推断",
    creative: "创意补全",
  };
  const STATUS_LABELS = {
    confirmed: "已确认",
    estimated: "估算",
    pending: "待确认",
    conflict: "冲突",
  };
  const REFERENCE_ROLE_LABELS = {
    identity: "身份参考",
    style: "风格参考",
    costume: "服装参考",
    scene: "场景参考",
  };
  const SUBTYPE_LABELS = { costume: "服装", hair: "发型 / 胡须", makeup: "妆容 / 彩绘" };
  const MEDIA_LABELS = { image: "图片", audio: "声音" };
  const MODE_LABELS = { generate: "生成", edit: "编辑" };
  const COVERAGE_LABELS = { present: "已发现", none: "未发现" };
  const FACT_KEY_LABELS = {
    render_mode: "渲染模式",
    height_cm: "身高",
    weight_kg: "体重",
  };

  const data = JSON.parse(document.getElementById("report-data").textContent);
  const assets = new Map(data.assets.map((asset) => [asset.id, asset]));
  const referenceInputs = new Map(data.reference_inputs.map((item) => [item.id, item]));
  const prompts = new Map();
  data.assets.forEach((asset) => asset.versions.forEach((version) => {
    version.prompts.forEach((prompt) => prompts.set(prompt.id, prompt));
  }));
  const app = document.getElementById("app");
  const toast = document.getElementById("copy-status");
  let idCounter = 0;
  let toastTimer;

  document.getElementById("report-title").textContent = data.title;
  document.getElementById("report-summary").textContent = data.input_summary;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function nextId(prefix) {
    idCounter += 1;
    return `${prefix}-${idCounter}`;
  }

  function showToast(message) {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add("is-visible");
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 1800);
  }

  function fallbackCopy(text) {
    const input = document.createElement("textarea");
    input.value = text;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    input.style.pointerEvents = "none";
    document.body.append(input);
    input.focus();
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    if (!copied) throw new Error("浏览器未允许复制");
  }

  async function copyPrompt(text, button) {
    try {
      let copied = false;
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text);
          copied = true;
        } catch (_) {
          copied = false;
        }
      }
      if (!copied) fallbackCopy(text);
      const original = button.textContent;
      button.textContent = "已复制";
      showToast("提示词已复制");
      setTimeout(() => { button.textContent = button.dataset.idleLabel || original; }, 1400);
    } catch (error) {
      showToast(`复制失败：${error.message}，请手动选择文本`);
    }
  }

  function createTabSet(items, label, nested = false, modifier = "") {
    const wrapper = element("div");
    if (!items.length) {
      wrapper.append(element("p", "empty-state", `未发现相关${label}`));
      return wrapper;
    }
    const classes = ["tab-list"];
    if (nested) classes.push("tab-list--nested");
    if (modifier) classes.push(`tab-list--${modifier}`);
    const tabList = element("div", classes.join(" "));
    tabList.setAttribute("role", "tablist");
    tabList.setAttribute("aria-label", label);
    const buttons = [];
    const panels = [];

    items.forEach((item, index) => {
      const tabId = nextId("tab");
      const panelId = nextId("panel");
      const button = element("button", "tab-button", item.label);
      button.type = "button";
      button.id = tabId;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-controls", panelId);
      button.setAttribute("aria-selected", index === 0 ? "true" : "false");
      button.tabIndex = index === 0 ? 0 : -1;
      const panel = element("section");
      panel.id = panelId;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", tabId);
      panel.hidden = index !== 0;
      panel.append(item.render());
      button.addEventListener("click", () => activate(index));
      buttons.push(button);
      panels.push(panel);
      tabList.append(button);
    });

    function activate(index, focus = false) {
      buttons.forEach((button, buttonIndex) => {
        const active = buttonIndex === index;
        button.setAttribute("aria-selected", active ? "true" : "false");
        button.tabIndex = active ? 0 : -1;
        panels[buttonIndex].hidden = !active;
      });
      if (focus) buttons[index].focus();
    }

    tabList.addEventListener("keydown", (event) => {
      const current = buttons.indexOf(document.activeElement);
      if (current < 0) return;
      let target = current;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") target = (current + 1) % buttons.length;
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") target = (current - 1 + buttons.length) % buttons.length;
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = buttons.length - 1;
      else return;
      event.preventDefault();
      activate(target, true);
    });
    wrapper.append(tabList, ...panels);
    return wrapper;
  }

  function createTable(headers, rows) {
    const wrap = element("div", "table-wrap");
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((label) => headRow.append(element("th", "", label)));
    head.append(headRow);
    const body = document.createElement("tbody");
    rows.forEach((cells) => {
      const row = document.createElement("tr");
      cells.forEach((cell) => row.append(element("td", "", cell)));
      body.append(row);
    });
    table.append(head, body);
    wrap.append(table);
    return wrap;
  }

  function resolveRef(ref) {
    const asset = assets.get(ref.asset_id);
    const version = asset.versions.find((item) => item.id === ref.version);
    return { ref, asset, version };
  }

  function addMetadata(list, label, value) {
    if (!value) return;
    const wrapper = document.createElement("div");
    wrapper.append(element("dt", "", label), element("dd", "", value));
    list.append(wrapper);
  }

  function renderFacts(title, facts) {
    if (!facts.length) return null;
    const section = element("section", "facts-section");
    section.append(element("h4", "subsection-title", title));
    section.append(createTable(
      ["事实", "值", "来源", "状态", "依据", "位置"],
      facts.map((fact) => [
        FACT_KEY_LABELS[fact.key] || fact.key,
        `${String(fact.value)}${fact.unit ? ` ${fact.unit}` : ""}`,
        SOURCE_LABELS[fact.source],
        STATUS_LABELS[fact.status],
        fact.evidence,
        fact.source_locator || "",
      ]),
    ));
    return section;
  }

  function formatOutputSpec(spec) {
    const parts = [`${MEDIA_LABELS[spec.media_type]} × ${spec.count}`];
    if (spec.layout) parts.push(spec.layout);
    if (spec.aspect_ratio) parts.push(`画幅 ${spec.aspect_ratio}`);
    if (spec.duration_seconds) parts.push(`${spec.duration_seconds} 秒`);
    if (spec.loopable !== undefined) parts.push(spec.loopable ? "可循环" : "不可循环");
    return parts.join(" · ");
  }

  function formatPromptInput(input) {
    if (input.source_kind === "reference_input") {
      const reference = referenceInputs.get(input.ref_id);
      return `${input.ref_id} · ${REFERENCE_ROLE_LABELS[reference.role]}：${input.role}`;
    }
    const prompt = prompts.get(input.ref_id);
    return `${input.ref_id} · ${prompt.label}：${input.role}`;
  }

  function categoryKey(asset) {
    return asset.type === "W" ? `W:${asset.subtype}` : asset.type;
  }

  function renderPrompt(prompt) {
    const card = element("section", "prompt-card");
    const header = element("div", "prompt-card__header");
    const title = element("div");
    title.append(element("h4", "", prompt.label));
    const badges = element("div", "badge-row prompt-badges");
    badges.append(
      element("span", "badge badge--muted", prompt.id),
      element("span", "badge", MODE_LABELS[prompt.mode]),
      element("span", "badge badge--warm", MEDIA_LABELS[prompt.output_spec.media_type]),
    );
    title.append(badges);
    const actions = element("div", "prompt-actions");
    const copyButton = element("button", "copy-button", "复制中文提示词");
    copyButton.type = "button";
    copyButton.dataset.idleLabel = "复制中文提示词";
    copyButton.setAttribute("aria-label", `复制${prompt.label}中文提示词`);
    let activeText = prompt.text;
    const promptText = element("pre", "", prompt.text);
    copyButton.addEventListener("click", () => copyPrompt(activeText, copyButton));
    const languageButton = element("button", "language-toggle", "查看英文版本");
    languageButton.type = "button";
    languageButton.setAttribute("aria-pressed", "false");
    languageButton.setAttribute("aria-label", `查看${prompt.label}英文版本`);
    languageButton.addEventListener("click", () => {
      const showEnglish = languageButton.getAttribute("aria-pressed") !== "true";
      languageButton.setAttribute("aria-pressed", showEnglish ? "true" : "false");
      languageButton.textContent = showEnglish ? "查看中文版本" : "查看英文版本";
      languageButton.setAttribute("aria-label", `查看${prompt.label}${showEnglish ? "中文" : "英文"}版本`);
      activeText = showEnglish ? prompt.text_en : prompt.text;
      promptText.textContent = activeText;
      copyButton.dataset.idleLabel = showEnglish ? "复制英文提示词" : "复制中文提示词";
      copyButton.textContent = copyButton.dataset.idleLabel;
      copyButton.setAttribute("aria-label", `复制${prompt.label}${showEnglish ? "英文" : "中文"}提示词`);
    });
    actions.append(languageButton);
    actions.append(copyButton);
    header.append(title, actions);
    card.append(header);

    const details = element("div", "prompt-details");
    details.append(element("p", "", `输出：${formatOutputSpec(prompt.output_spec)}`));
    if (prompt.input_refs.length) {
      details.append(element("p", "prompt-detail-title", "输入依赖"));
      const list = element("ul", "plain-list prompt-inputs");
      prompt.input_refs.forEach((input) => list.append(element("li", "", formatPromptInput(input))));
      details.append(list);
    } else {
      details.append(element("p", "", "输入：无，直接生成"));
    }
    card.append(details, promptText);
    return card;
  }

  function renderAssetCard(resolved) {
    const { ref, asset, version } = resolved;
    const card = element("article", "asset-card");
    const header = element("header", "asset-card__header");
    const titleBlock = element("div");
    const badges = element("div", "badge-row");
    badges.append(
      element("span", "badge", `${asset.type} · ${TYPE_LABELS[asset.type]}`),
      element("span", "badge badge--warm", ref.relation_label),
      element("span", "badge badge--muted", version.label),
    );
    titleBlock.append(badges, element("h3", "", `${asset.id} ${asset.name}`));
    header.append(titleBlock);
    card.append(header);

    const metadata = element("dl", "metadata");
    addMetadata(metadata, "首次出现", asset.first_appearance);
    addMetadata(metadata, "重要性", asset.importance_level ? `${asset.importance_level} 级` : "");
    addMetadata(metadata, "子类型", asset.subtype ? SUBTYPE_LABELS[asset.subtype] : "");
    addMetadata(metadata, "故事阶段", version.story_stage);
    addMetadata(metadata, "资产定义", asset.definition);
    addMetadata(metadata, "一致性锚点", asset.anchors.join("\n"));
    addMetadata(metadata, "本版本变化", version.changes);
    if (metadata.children.length) card.append(metadata);

    const stableFacts = renderFacts("稳定事实", asset.facts);
    const versionFacts = renderFacts("版本事实", version.facts);
    if (stableFacts) card.append(stableFacts);
    if (versionFacts) card.append(versionFacts);

    const promptList = element("div", "prompt-list");
    version.prompts.forEach((prompt) => promptList.append(renderPrompt(prompt)));
    card.append(promptList);

    if (version.prohibitions.length) {
      const list = element("ul", "prohibitions");
      version.prohibitions.forEach((item) => list.append(element("li", "", item)));
      card.append(list);
    }
    return card;
  }

  function renderRefs(title, refs) {
    const section = element("section", "state-heading");
    section.append(element("h2", "", title));
    if (!refs.length) {
      section.append(element("p", "empty-state", "未发现相关资产"));
      return section;
    }
    refs.map(resolveRef)
      .sort((left, right) => left.asset.id.localeCompare(right.asset.id) || left.version.id.localeCompare(right.version.id))
      .forEach((item) => section.append(renderAssetCard(item)));
    return section;
  }

  function renderCategorizedContexts(contexts, label, preferredCategory = "") {
    const categories = CATEGORY_ORDER.map((key) => {
      const filteredContexts = contexts.map((context) => ({
        label: context.label,
        refs: context.refs.filter((ref) => categoryKey(assets.get(ref.asset_id)) === key),
      })).filter((context) => context.refs.length);
      const uniqueRefs = new Set(filteredContexts.flatMap((context) => (
        context.refs.map((ref) => `${ref.asset_id}:${ref.version}`)
      )));
      return {
        key,
        label: `${CATEGORY_LABELS[key]} ${uniqueRefs.size}`,
        render: () => {
          const content = element("div", "section-stack");
          filteredContexts.forEach((context) => content.append(renderRefs(context.label, context.refs)));
          return content;
        },
        count: uniqueRefs.size,
      };
    }).filter((category) => category.count);
    if (preferredCategory) {
      categories.sort((left, right) => (
        Number(right.key === preferredCategory) - Number(left.key === preferredCategory)
        || CATEGORY_ORDER.indexOf(left.key) - CATEGORY_ORDER.indexOf(right.key)
      ));
    }
    return createTabSet(categories, label, true, "category");
  }

  function renderEntity(entity) {
    const content = element("div", "section-stack");
    const heading = element("header", "entity-heading");
    heading.append(
      element("p", "eyebrow", ENTITY_LABELS[entity.type]),
      element("h2", "", entity.name),
    );
    if (entity.description) heading.append(element("p", "", entity.description));
    const contexts = [{ label: "共用资产", refs: entity.common_asset_refs }];
    entity.states.forEach((state) => contexts.push({
      label: state.story_stage ? `${state.label} · ${state.story_stage}` : state.label,
      refs: state.asset_refs,
    }));
    const preferredCategory = entity.type === "character" ? "C" : "S";
    content.append(heading, renderCategorizedContexts(contexts, `${entity.name}资产分类`, preferredCategory));
    return content;
  }

  function renderEntityType(type, label) {
    const entities = data.entities.filter((entity) => entity.type === type);
    return createTabSet(
      entities.map((entity) => ({ label: entity.name, render: () => renderEntity(entity) })),
      `${label}实体`,
      true,
      "entity",
    );
  }

  function renderStandalone() {
    const refs = data.standalone_asset_refs.filter((ref) => assets.get(ref.asset_id).type !== "G");
    return renderCategorizedContexts([{ label: "独立资产", refs }], "独立资产分类");
  }

  function renderListSection(title, items, emptyText) {
    const section = element("section", "report-section");
    section.append(element("h2", "", title));
    if (!items.length) {
      section.append(element("p", "empty-state", emptyText));
      return section;
    }
    const list = element("ul", "plain-list");
    items.forEach((item) => list.append(element("li", "", item)));
    section.append(list);
    return section;
  }

  function renderAliases() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "别名表"));
    if (!data.aliases.length) {
      section.append(element("p", "empty-state", "未发现需要合并的别名"));
      return section;
    }
    section.append(createTable(
      ["别名", "规范名称", "说明"],
      data.aliases.map((alias) => [alias.alias, alias.canonical, alias.note || ""]),
    ));
    return section;
  }

  function renderReferenceInputs() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "用户参考图"));
    if (!data.reference_inputs.length) {
      section.append(element("p", "empty-state", "未提供用户参考图"));
      return section;
    }
    section.append(createTable(
      ["编号", "职责", "来源", "说明", "允许影响", "禁止影响"],
      data.reference_inputs.map((item) => [
        item.id,
        REFERENCE_ROLE_LABELS[item.role],
        item.source_ref,
        item.description,
        item.allowed_influence.join("；"),
        item.prohibited_influence.join("；"),
      ]),
    ));
    return section;
  }

  function renderCoverage() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "资产类型覆盖"));
    const byType = new Map(data.asset_type_coverage.map((item) => [item.type, item]));
    section.append(createTable(
      ["类型", "状态", "数量", "说明"],
      TYPE_ORDER.map((type) => {
        const item = byType.get(type);
        return [`${type} · ${TYPE_LABELS[type]}`, COVERAGE_LABELS[item.status], String(item.count), item.note || ""];
      }),
    ));
    return section;
  }

  function renderAssetTable() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "资产总表"));
    section.append(createTable(
      ["编号", "类型", "名称", "重要性", "子类型", "首次出现", "版本数"],
      [...data.assets]
        .sort((left, right) => TYPE_ORDER.indexOf(left.type) - TYPE_ORDER.indexOf(right.type) || left.id.localeCompare(right.id))
        .map((asset) => [
          asset.id,
          TYPE_LABELS[asset.type],
          asset.name,
          asset.importance_level || "",
          asset.subtype ? SUBTYPE_LABELS[asset.subtype] : "",
          asset.first_appearance || "",
          String(asset.versions.length),
        ]),
    ));
    return section;
  }

  function renderContinuity() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "阶段连贯性"));
    if (!data.continuity.length) {
      section.append(element("p", "empty-state", "未提供连贯性记录"));
      return section;
    }
    section.append(createTable(
      ["阶段", "名称", "原文位置", "资产版本"],
      data.continuity.map((stage) => [
        stage.stage_id,
        stage.label,
        stage.source_locator,
        stage.asset_refs.map((ref) => `${ref.asset_id}-${ref.version}（${ref.relation_label}）`).join("\n"),
      ]),
    ));
    return section;
  }

  function renderQualityChecks() {
    const section = element("section", "report-section");
    section.append(element("h2", "", "质量检查"));
    const list = element("div", "quality-list");
    const structural = element("div", "quality-item");
    structural.append(
      element("span", "badge", "结构通过"),
      element("p", "", "Manifest V2 已由渲染器完成结构、引用和依赖校验。"),
    );
    list.append(structural);
    data.quality_checks.forEach((check) => {
      const item = element("div", "quality-item");
      const badgeClass = check.status === "pass" ? "badge" : check.status === "warning" ? "badge badge--warm" : "badge badge--muted";
      item.append(
        element("span", badgeClass, `语义${QUALITY_LABELS[check.status]}`),
        element("p", "", check.note ? `${check.label}：${check.note}` : check.label),
      );
      list.append(item);
    });
    section.append(list);
    return section;
  }

  function renderProjectReport() {
    const content = element("div", "section-stack");
    const summary = element("section", "report-section");
    summary.append(
      element("h2", "", "输入摘要"),
      element("p", "page-summary", data.input_summary),
      element("p", "schema-version", `Schema：${data.schema_version}`),
    );
    content.append(
      summary,
      renderListSection("用户约束", data.constraints, "未提供额外约束"),
      renderAliases(),
      renderReferenceInputs(),
      renderListSection("待确认问题", data.pending_questions, "没有待确认问题"),
    );
    const globalRefs = [];
    data.assets.filter((asset) => asset.type === "G").forEach((asset) => {
      asset.versions.forEach((version) => globalRefs.push({
        asset_id: asset.id,
        version: version.id,
        relation_label: "项目全局",
      }));
    });
    content.append(
      renderRefs("全局视觉资产", globalRefs),
      renderCoverage(),
      renderAssetTable(),
      renderContinuity(),
      renderQualityChecks(),
    );
    return content;
  }

  try {
    const characterCount = data.entities.filter((entity) => entity.type === "character").length;
    const sceneCount = data.entities.filter((entity) => entity.type === "scene").length;
    const standaloneCount = data.standalone_asset_refs.filter((ref) => assets.get(ref.asset_id).type !== "G").length;
    app.append(createTabSet([
      { label: `角色 ${characterCount}`, render: () => renderEntityType("character", "角色") },
      { label: `场景 ${sceneCount}`, render: () => renderEntityType("scene", "场景") },
      { label: `独立资产 ${standaloneCount}`, render: renderStandalone },
      { label: "项目报告", render: renderProjectReport },
    ], "报告分类"));
  } catch (error) {
    const failure = element("section", "report-section");
    failure.append(element("h2", "", "报告加载失败"), element("p", "empty-state", error.message));
    app.append(failure);
  }
})();
