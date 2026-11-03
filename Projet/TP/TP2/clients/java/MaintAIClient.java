import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Client Java de l'API MaintAI : la même requête que la page web, curl.exe ou les tests.
 *
 * La clé n'est pas dans le code : elle est lue dans la variable d'environnement MAINTAI_API_KEY.
 *
 * Windows (cmd) :
 *   set MAINTAI_API_KEY=ma-cle
 *   java clients\java\MaintAIClient.java
 * PowerShell : $env:MAINTAI_API_KEY="ma-cle" puis la même commande.
 * (Java 11+ exécute directement un fichier .java, sans javac.)
 */
public class MaintAIClient {

    public static void main(String[] args) throws Exception {
        String url = System.getenv().getOrDefault("MAINTAI_URL", "http://localhost:8000");
        String key = System.getenv("MAINTAI_API_KEY");
        if (key == null || key.isBlank()) {
            System.err.println("Définissez MAINTAI_API_KEY avant de lancer le client.");
            System.exit(1);
        }

        String reading = """
            {"temperature_c": 60.0, "vibration_mm_s": 2.0, "load_pct": 50.0, "runtime_hours": 5000}
            """;

        HttpRequest request = HttpRequest.newBuilder(URI.create(url + "/v1/predict"))
                .header("Content-Type", "application/json")
                .header("X-API-Key", key)
                .POST(HttpRequest.BodyPublishers.ofString(reading))
                .build();

        try {
            // HTTP/1.1 : par défaut Java tente une montée en HTTP/2 qu'uvicorn refuse (400)
            HttpClient http = HttpClient.newBuilder()
                    .version(HttpClient.Version.HTTP_1_1)
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            System.out.println("HTTP " + response.statusCode());
            System.out.println(response.body());
        } catch (java.net.ConnectException e) {
            System.err.println("API injoignable sur " + url + " : uvicorn est-il lancé ?");
            System.exit(2);
        }
    }
}
