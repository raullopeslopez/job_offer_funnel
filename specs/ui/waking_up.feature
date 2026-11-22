Feature: Waking up the server
  As a job seeker
  I want to see that the app is loading when I open it
  So that a slow first answer does not look like an empty inbox

  The API runs on a plan that sleeps it after a while without requests, and its
  database suspends too: the first request after a pause can take up to a minute.
  Every screen asks the API for the number of pending offers (the count in the
  navigation), so until that first answer arrives the content is covered by a loading
  animation; the screen's own requests are sent at the same time, underneath. After a
  few seconds without an answer the animation also says the server is waking up and
  that it can take up to a minute. If the request fails, the animation gives way to a
  message with a button to try again. Once it has answered once, the animation does
  not come back until the app is opened again.

  @component
  Scenario: The content is covered until the API answers
    Given the API has not answered yet
    When I open the app
    Then I see the loading animation
    And I do not see the content of the screen

  @component
  Scenario: A slow answer says the server is waking up
    Given the API has not answered after a few seconds
    When I open the app
    Then I see "Waking up the server. It can take up to a minute."

  @component
  Scenario: The content shows once the API answers
    Given the API answers after a while
    When I open the app
    Then I no longer see the loading animation
    And I see the content of the screen

  @component
  Scenario: A failed answer can be tried again
    Given the API fails to answer
    When I open the app
    Then I see "The server did not answer."
    When I try again and the API answers
    Then I see the content of the screen
