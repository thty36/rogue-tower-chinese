// Rogue Tower 语言切换插件（BepInEx 5, Unity 2021 Mono x86）
// 运行时在 Text 渲染入口翻译：游戏资源文件保持英文原版，逻辑零改动。
// 右上角悬浮按钮点击切换 中/EN；默认中文。
using System;
using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

[BepInPlugin("cn.roguetower.langtoggle", "RogueTower LangToggle", "1.0.0")]
public class LangTogglePlugin : BaseUnityPlugin
{
    public static bool Chinese = true;
    public static readonly Dictionary<string, string> ZH = new Dictionary<string, string>();
    public static readonly Dictionary<string, string> EN = new Dictionary<string, string>();
    public static Font ZhFont;
    public static Font EnFont;
    public static Text ButtonLabel;

    static Harmony _harmony;

    void Awake()
    {
        LangTable.Fill(ZH);
        foreach (var kv in ZH)
            if (!EN.ContainsKey(kv.Value))
                EN[kv.Value] = kv.Key;

        ZhFont = Font.CreateDynamicFontFromOSFont(new string[] {
            "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "SimHei", "黑体"}, 16);

        _harmony = new Harmony("cn.roguetower.langtoggle");
        _harmony.PatchAll(typeof(Patches));

        SceneManager.sceneLoaded += delegate (Scene s, LoadSceneMode m)
        {
            Sweep();
        };

        MakeButton();
        StartCoroutine(InitWhenReady());
        UnityEngine.Debug.Log("[LangToggle] awake, dict=" + ZH.Count);
    }

    IEnumerator InitWhenReady()
    {
        // 等待 Acme 字体加载后做首次全量处理（首个场景的 OnEnable 早于插件）
        int waited = 0;
        while (EnFont == null && waited < 600)
        {
            foreach (Font f in Resources.FindObjectsOfTypeAll<Font>())
            {
                if (f != null && f.name == "Acme-Regular") { EnFont = f; break; }
            }
            if (EnFont == null)
            {
                waited++;
                yield return new WaitForSeconds(0.1f);
            }
        }
        Sweep();
    }

    public static void Sweep()
    {
        // 全量处理当前已存在的 Text（场景反序列化的文本不会经过 set_text）
        Text[] texts = Resources.FindObjectsOfTypeAll<Text>();
        for (int i = 0; i < texts.Length; i++)
            Apply(texts[i], true);
    }

    public static void Apply(Text t, bool allowSet)
    {
        if (t == null) return;
        try
        {
            if (Chinese)
            {
                if (ZhFont != null && t.font != ZhFont) t.font = ZhFont;
                if (allowSet && t.text != null)
                {
                    string zh;
                    if (ZH.TryGetValue(t.text, out zh)) t.text = zh;
                    else t.text = TranslateRuntimeBuilt(t.text);
                }
            }
            else
            {
                if (EnFont != null && t.font == ZhFont) t.font = EnFont;
                if (allowSet && t.text != null)
                {
                    string en;
                    if (EN.TryGetValue(t.text, out en)) t.text = en;
                }
            }
        }
        catch (Exception)
        {
            // 场景卸载中的对象，忽略
        }
    }

    // 代码在运行时拼接的文本（含数字），词典无法整句命中，这里做模板级翻译
    static readonly Regex ReTreeTip = new Regex(
        @"^Chopping this tree will currently yield (\d+)g\.?\s*\nAnd, a (\d+)% chance of dropping cards\.?\s*$",
        RegexOptions.Compiled);
    static readonly Regex ReTreeTipNoCard = new Regex(
        @"^Chopping this tree will currently yield (\d+)g\.?\s*$",
        RegexOptions.Compiled);

    public static string TranslateRuntimeBuilt(string s)
    {
        if (string.IsNullOrEmpty(s)) return s;
        if (s.Length < 8) return s;
        if (s.StartsWith("Unlocked Achievement: ", StringComparison.Ordinal))
            return "已解锁成就：" + s.Substring(23);
        Match m = ReTreeTip.Match(s);
        if (m.Success)
            return "砍倒这棵树当前可获得 " + m.Groups[1].Value + " 金币。\n另有 " + m.Groups[2].Value + "% 的几率掉落卡牌。";
        m = ReTreeTipNoCard.Match(s);
        if (m.Success)
            return "砍倒这棵树当前可获得 " + m.Groups[1].Value + " 金币。";
        return s;
    }

    void MakeButton()
    {
        GameObject root = new GameObject("LangToggleRoot");
        UnityEngine.Object.DontDestroyOnLoad(root);
        Canvas cv = root.AddComponent<Canvas>();
        cv.renderMode = RenderMode.ScreenSpaceOverlay;
        cv.sortingOrder = 30000;
        root.AddComponent<GraphicRaycaster>();

        GameObject btnGo = new GameObject("LangToggleButton");
        btnGo.transform.SetParent(root.transform, false);
        Image img = btnGo.AddComponent<Image>();
        img.color = new Color(0f, 0f, 0f, 0.55f);
        Button btn = btnGo.AddComponent<Button>();
        btn.targetGraphic = img;

        GameObject lblGo = new GameObject("Label");
        lblGo.transform.SetParent(btnGo.transform, false);
        ButtonLabel = lblGo.AddComponent<Text>();
        ButtonLabel.font = ZhFont;
        ButtonLabel.fontSize = 16;
        ButtonLabel.alignment = TextAnchor.MiddleCenter;
        ButtonLabel.color = Color.white;
        ButtonLabel.text = "中/EN";
        ButtonLabel.raycastTarget = false;
        RectTransform lblRt = ButtonLabel.rectTransform;
        lblRt.anchorMin = Vector2.zero;
        lblRt.anchorMax = Vector2.one;
        lblRt.offsetMin = Vector2.zero;
        lblRt.offsetMax = Vector2.zero;

        RectTransform rt = btnGo.GetComponent<RectTransform>();
        rt.anchorMin = new Vector2(1f, 1f);
        rt.anchorMax = new Vector2(1f, 1f);
        rt.pivot = new Vector2(1f, 1f);
        rt.anchoredPosition = new Vector2(-6f, -6f);
        rt.sizeDelta = new Vector2(76f, 32f);

        btn.onClick.AddListener(new UnityAction(OnToggleClicked));
    }

    void OnToggleClicked()
    {
        Chinese = !Chinese;
        Sweep();
        UpdateButtonLabel();
        UnityEngine.Debug.Log("[LangToggle] mode -> " + (Chinese ? "Chinese" : "English"));
    }

    public static void UpdateButtonLabel()
    {
        if (ButtonLabel != null)
            ButtonLabel.text = Chinese ? "中/EN" : "EN/中";
    }
}

[HarmonyPatch]
public static class Patches
{
    // 拦截所有 UI 文本设置：中文模式下查词典替换（找不到原样通过）
    [HarmonyPrefix]
    [HarmonyPatch(typeof(Text), "text", MethodType.Setter)]
    static void PreSetText(ref string value)
    {
        if (!LangTogglePlugin.Chinese || value == null) return;
        string zh;
        if (LangTogglePlugin.ZH.TryGetValue(value, out zh))
        {
            value = zh;
            return;
        }
        if (value.Length >= 8)
            value = LangTogglePlugin.TranslateRuntimeBuilt(value);
    }

    // Text 激活时校正字体并翻译反序列化的存量文本（新建/实例化/重新启用的 UI 都会走这里）
    [HarmonyPostfix]
    [HarmonyPatch(typeof(Graphic), "OnEnable")]
    static void PostOnEnable(Graphic __instance)
    {
        Text t = __instance as Text;
        if (t != null) LangTogglePlugin.Apply(t, true);
    }
}
