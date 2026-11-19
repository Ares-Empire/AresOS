package dev.aresos.config;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class AppSearchTest {
    private static AppDefinition app(String id, String name, String genericName, String... keywords) {
        return new AppDefinition(id, name, List.of(), "minecraft:paper", false, "helper", null, null)
                .withSystem(new SystemInfo("system", null, null, genericName, keywords.length == 0 ? null : List.of(keywords),
                        null, null, null));
    }

    private static final List<AppDefinition> APPS = List.of(
            app("okular", "Okular", "Document Viewer", "pdf", "epub"),
            app("thunderbird", "Thunderbird", "Mail Client", "Email", "newsgroup"),
            app("kmail", "KMail", "Mail Client"),
            app("ark", "Ark", "Archiving Tool", "zip", "tar"),
            // No word from the system at all: only the name can be searched.
            new AppDefinition("notes", "My Notes", List.of("notes.exe"), "minecraft:book", false));

    private static List<String> found(String query) {
        return AppSearch.find(APPS, query).stream().map(AppDefinition::id).toList();
    }

    @Test void savedShortNamesAreSearchableEvenWhenTheyAreNotPartOfTheName() {
        var discord = app("discord", "Discord", "Messenger").withMine(true).withNames(List.of("chat", "dc"));
        assertEquals(List.of(discord), AppSearch.find(List.of(discord), "DC"));
        assertEquals(List.of(discord), AppSearch.find(List.of(discord), "chat"));
        assertEquals(List.of(), AppSearch.find(List.of(discord), "chatdc"));
    }

    @Test void anEmptySearchListsEveryProgramByName() {
        assertEquals(List.of("ark", "kmail", "notes", "okular", "thunderbird"), found(""));
        assertEquals(found(""), found("   "));
    }

    @Test void looksInTheNameTheGenericNameAndTheKeywords() {
        assertEquals(List.of("okular"), found("oku"));
        assertEquals(List.of("okular"), found("pdf"));
        assertEquals(List.of("kmail", "thunderbird"), found("mail"));
        assertEquals(List.of("ark"), found("archiv"));
        assertEquals(List.of("notes"), found("notes"));
        assertEquals(List.of(), found("spreadsheet"));
    }

    @Test void upperAndLowerCaseAreOne() {
        assertEquals(List.of("thunderbird"), found("EMAIL"));
        assertEquals(List.of("kmail"), found("kMAIL"));
    }

    @Test void everyWordMustBeFoundAndNoWordSpansTwoFields() {
        assertEquals(List.of("thunderbird"), found("mail thunder"));
        assertEquals(List.of("okular"), found("  viewer   pdf "));
        assertEquals(List.of(), found("mail pdf"));
        // "Viewer" ends the generic name and "pdf" starts the keywords: together they are not a word of Okular.
        assertEquals(List.of(), found("viewerpdf"));
    }

    @Test void twoProgramsWithOneNameKeepAFixedOrder() {
        var twins = List.of(app("b-notes", "Notes", null), app("a-notes", "notes", null));
        assertEquals(List.of("a-notes", "b-notes"), AppSearch.find(twins, "").stream().map(AppDefinition::id).toList());
    }

    // Package 53d: the order of the search over the world, whose first hit Enter opens.

    private static final List<AppDefinition> RANKED = List.of(
            app("cobweb", "Cobweb Test", "Game").withMine(true).withNames(List.of("cobweb")),
            app("web-1", "Test Web 1", "Web Browser").withMine(true).withNames(List.of("web1")),
            app("webcam", "Webcam Test", "Camera"),
            app("web-2", "Test Web 2", "Web Browser"),
            app("feeds", "Test Feeds", "Web Feed Reader"),
            app("cobweb-viewer", "Cobweb Viewer", null),
            app("chat", "Test Chat", "Messenger").withMine(true).withNames(List.of("tc")));

    private static List<String> ranked(String query) {
        return AppSearch.ranked(RANKED, query).stream().map(AppDefinition::id).toList();
    }

    @Test void hisAppsComeFirstThenAStartOfTheNameOrOfAWordThenTheName() {
        // His two first, the one whose word starts with it before the one that has it inside a word, though C sorts
        // before T. Then the others the same way; a hit only in the generic name counts as one inside a word.
        assertEquals(List.of("web-1", "cobweb", "web-2", "webcam", "cobweb-viewer", "feeds"), ranked("web"));
        assertEquals("web-1", AppSearch.best(RANKED, "web").id());
        // The same programs as the Apps screen's search finds, only in another order.
        assertEquals(AppSearch.find(RANKED, "web").stream().map(AppDefinition::id).sorted().toList(),
                ranked("web").stream().sorted().toList());
    }

    @Test void aShortNameCountsAsAStart() {
        // "tc" is nowhere in "Test Chat": his short name alone finds it, and it is a start.
        assertEquals(List.of("chat"), ranked("tc"));
        assertEquals(List.of("web-1", "cobweb", "web-2", "webcam", "cobweb-viewer", "feeds"), ranked("WEB"));
    }

    @Test void everyWordOfTheQueryMustStartAWordToCountAsAStart() {
        // "test web": both words start words of "Test Web 2"; in "Webcam Test" too. "Cobweb Test" has web inside.
        assertEquals(List.of("web-1", "cobweb", "web-2", "webcam", "feeds"), ranked("test web"));
    }

    @Test void aBlankQueryHasNoBestHitAndListsHisAppsFirst() {
        assertNull(AppSearch.best(RANKED, ""));
        assertNull(AppSearch.best(RANKED, "   "));
        assertNull(AppSearch.best(RANKED, "spreadsheet"));
        assertEquals(List.of("cobweb", "chat", "web-1", "cobweb-viewer", "feeds", "web-2", "webcam"), ranked(""));
    }
}
