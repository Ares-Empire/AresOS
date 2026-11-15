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
}
