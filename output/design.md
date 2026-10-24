# Campus Customs: Design (Problem 10)

## The idea: "Game-day stitching"

Campus Customs sells Yale apparel from a shop at 57 Broadway, so we built the site out of the materials of the merch itself: **Yale-blue felt, chenille varsity letters, stitched seams, kraft hang tags, and heather-gray fleece.** The site should feel like walking up to the counter, not like a generic store template. Every element below comes from that one idea.

## What we changed and why

| Change | What it looks like | Why it should help people stay and buy |
|---|---|---|
| **Stitched chenille hero** | "BULLDOG BLUE" as a giant varsity letter. On page load the letters fill in like embroidery, then a dashed stitch line sews around them (about 2 seconds, once). | It's the one bold moment, and it says "Yale gear" in under a second, before anyone reads a word. A memorable first screen gives shoppers a reason to scroll. |
| **Varsity + Franklin type** | **Graduate** (a collegiate varsity face) for headings, prices, and sizes. **Libre Franklin** (the Franklin Gothic of athletic programs) for reading. Both are self-hosted, so the site never shows a fallback font. | Instantly reads as college apparel. Prices in the varsity face look like printed merch tags, not spreadsheet numbers. |
| **Felt and heather textures** | A faint fiber grain on every Yale-blue surface (nav, hero, chat, footer) and on the heather-gray page background. It's drawn with an inline SVG, so there's nothing extra to download. | It feels like fabric. Shoppers buying sweatshirts sense the material even on a screen, which builds confidence in what they're buying. |
| **Products as hang tags** | Each photo hangs a notched **kraft tag** on a string holding the name, varsity price, and blurb. On hover the tag swings. | It's presented like merch on a rack, so the price is exactly where a shopper's eye goes on a real tag. The swing on hover is a small, satisfying response that invites clicking through. |
| **Sold out = crimson stamp** | A rotated rubber stamp in Harvard **crimson**, with the photo desaturated. On the product page, sold-out sizes are crossed off like retired jersey numbers. | Unmissable and honest: no one clicks into an item to discover it's gone. Using the rival's color for "sold out" is a wink Yale shoppers will notice. |
| **Jersey-tile sizes** | Big varsity size letters (XS–XXL) on white tiles. Green "25 in stock", amber "Only 5 left", crimson strike for sold out. | Shoppers find their size at a glance. "Only 5 left" adds honest urgency on items that are actually low. |
| **Price hang tag on the product page** | The price sits on a large, slightly tilted kraft tag with a punched hole. | Makes the price the clear second thing you read after the name, the way it is in the store. |
| **"Ask the counter" chat** | The launcher is a round **chenille patch** with a stitched ring that straightens up on hover. The panel has a felt header with a stitched border, a heather message area, and the assistant's replies marked with a Yale-blue rule. "Typing" shows a little thread being pulled. | Calling it "Ask the counter" frames the bot as the person behind the register, not a generic help widget, which makes people more likely to use it, and the chat is where shoppers find items fast. The patch is noticeable without a pop-up nagging them. |
| **Chat results on felt** | Products the chat finds land on the page in a Yale-blue felt band headed "Pulled from the back room for you", using the same hang-tag cards. The "6 items: Hoodies" note in the chat is a small kraft tag. | Makes it obvious the chat just changed the page, and the "back room" language makes it feel like personal service. |
| **Stitched details, used consistently** | Dashed "stitch" lines mark the active nav link, the ghost button, section dividers, the hero's bottom seam, the visit and login cards, and the selected category chip. | One repeated device makes the site feel designed rather than assembled, and it shows hierarchy ("you are here", "this is selected") without extra labels. |
| **Footer address mark** | "57 Broadway" in giant outlined varsity letters, stitched into the felt. | Ends every page by reminding people there's a real shop they can walk into, which builds trust for online buyers. |
| **Hierarchy and copy clean-up** | Removed the all-caps label lines above headings. Headings are varsity, body text is Franklin. CTAs say what they do ("Shop 102 styles", "Start with hoodies"). | Fewer competing labels means the eye goes headline → product → price → action. |

## Motion, kept on purpose

- **Plays on its own, once:** the hero embroidery on page load.
- **Responds to the shopper:** the tag swings on hover, the patch straightens on hover, the chat panel opens from the corner, and chat results drop in.
- **Reduced motion:** with "reduce motion" turned on, all of these are switched off.

## Palette

| Token | Hex | Used for |
|---|---|---|
| Yale blue | `#00356B` | Felt surfaces, prices, primary buttons |
| Ink | `#10233F` | Text |
| Heather | `#E6E9EE` | Page background (sweatshirt gray) |
| Kraft | `#D9B985` | Hang tags |
| Crimson | `#A51C30` | Sold out only |
| White | `#FFFFFF` | Stitching, photo fields |

## Quality floor

- **Phones:** works at phone width with no sideways scrolling. The product grid drops to two columns and the chat patch shrinks.
- **Keyboard:** visible focus outlines on every interactive element.
- **Images:** product photos keep alt text.
- **Screen readers:** the stitched wordmark is an SVG labeled "BULLDOG BLUE".
